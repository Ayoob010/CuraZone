from django.contrib import admin
from . import models
from .models import CommunityGroup, GroupMember, GroupMessage

@admin.register(CommunityGroup)
class CommunityGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'created_at')
    search_fields = ('name',)


@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display = ('group', 'user', 'joined_at')
    list_filter = ('group',)
    search_fields = ('user__username',)


@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display = ('group', 'user', 'message', 'timestamp')
    list_filter = ('group',)


class OrderItemInline(admin.TabularInline):
    model = getattr(models, 'OrderItem', None) or models.OrderItem # Safe access in case import issues but simple here
    # Actually I should fix imports first or assume .models is imported as models
    # user code has "from .models import CommunityGroup..."
    # I should update imports to "from .models import ..." including new ones or just *
    extra = 0

@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    inlines = [OrderItemInline]


