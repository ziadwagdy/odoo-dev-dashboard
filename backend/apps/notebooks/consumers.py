import asyncio, json, threading
from channels.generic.websocket import AsyncWebsocketConsumer
from . import kernel_manager


class NotebookConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.project = self.scope['url_route']['kwargs']['project']
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'status',
            'data': kernel_manager.get_kernel_status(self.project),
        }))

    async def receive(self, text_data):
        try:
            msg = json.loads(text_data)
            t = msg.get('type')
            if t == 'execute':
                await self.execute_cell(msg.get('code', ''), msg.get('cell_id', ''))
            elif t == 'start':
                await self.start_kernel(msg.get('db', ''))
            elif t == 'stop':
                kernel_manager.stop_kernel(self.project)
                await self.send(text_data=json.dumps({
                    'type': 'status',
                    'data': kernel_manager.get_kernel_status(self.project),
                }))
            elif t == 'interrupt':
                result = kernel_manager.interrupt_kernel(self.project)
                if not result.get('ok'):
                    await self.send(text_data=json.dumps({
                        'type': 'error', 'error': result.get('error', 'Interrupt failed'),
                    }))
        except Exception as exc:
            await self.send(text_data=json.dumps({'type': 'error', 'error': str(exc)}))

    async def start_kernel(self, db: str):
        if not db:
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'db required'}))
            return
        container = f'{self.project}-app'
        loop = asyncio.get_running_loop()

        def status_callback(text: str):
            asyncio.run_coroutine_threadsafe(
                self.send(text_data=json.dumps({'type': 'status_message', 'text': text})),
                loop,
            )

        result = await loop.run_in_executor(
            None,
            lambda: kernel_manager.start_kernel(self.project, container, db, status_callback),
        )
        payload = {'type': 'kernel_started' if result.get('ok') else 'error', 'data': result}
        if not result.get('ok'):
            payload['error'] = result.get('error', 'Unknown error')
        await self.send(text_data=json.dumps(payload))
        await self.send(text_data=json.dumps({
            'type': 'status',
            'data': kernel_manager.get_kernel_status(self.project),
        }))

    async def execute_cell(self, code: str, cell_id: str):
        loop = asyncio.get_running_loop()
        out_queue: asyncio.Queue = asyncio.Queue()

        def _callback(output_type: str, data, oi_cell_id: str):
            if output_type == 'stream':
                ws_type = data['name']   # 'stdout' or 'stderr'
                ws_data = data['text']
            else:
                ws_type = output_type    # 'html', 'image', 'text', 'error'
                ws_data = data
            loop.call_soon_threadsafe(out_queue.put_nowait, (ws_type, ws_data))

        def _run():
            kernel_manager.execute_code(self.project, cell_id, code, _callback)
            loop.call_soon_threadsafe(out_queue.put_nowait, None)

        threading.Thread(target=_run, daemon=True).start()

        while True:
            item = await out_queue.get()
            if item is None:
                await self.send(text_data=json.dumps({'type': 'done', 'cell_id': cell_id}))
                break
            output_type, data = item
            await self.send(text_data=json.dumps({
                'type': 'output', 'cell_id': cell_id,
                'output_type': output_type, 'data': data,
            }))

    async def disconnect(self, close_code):
        pass
