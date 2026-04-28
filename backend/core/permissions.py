from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Allows access only to users in the 'admin' group."""

    message = 'Admin privileges required.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name='admin').exists()
        )


class IsAdminOrManager(BasePermission):
    """Allows access to admin and manager users."""

    message = 'Manager or admin privileges required.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name__in=['admin', 'manager']).exists()
        )
