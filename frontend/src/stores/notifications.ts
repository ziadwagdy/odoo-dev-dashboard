import { defineStore } from 'pinia'
import { ref } from 'vue'

interface Notification {
  id: number
  type: 'success' | 'error' | 'info'
  message: string
}

let _id = 0

export const useNotificationsStore = defineStore('notifications', () => {
  const items = ref<Notification[]>([])

  function add(type: Notification['type'], message: string) {
    const id = ++_id
    items.value.push({ id, type, message })
    setTimeout(() => remove(id), 4000)
  }

  function remove(id: number) {
    items.value = items.value.filter(n => n.id !== id)
  }

  return { items, add, remove }
})
