from django import forms
from django.contrib import admin
from django.contrib.auth.models import User
from models import UserProfile, AuthToken, ResearchGroup, TestbedPermission, AuthorizedOfficial
from utils.admin import insert_inline
from utils.fields import MultiSelectFormField


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    max_num = 0


class AuthTokenInline(admin.TabularInline):
    model = AuthToken
    extra = 0


class TestbedPermissionInline(admin.TabularInline):
    model = TestbedPermission


class AuthorizedOfficialInline(admin.StackedInline):
    model = AuthorizedOfficial


def action(testbdepermission):
    return str(testbdepermission.action)


class TestbedPermissionAdmin(admin.ModelAdmin):
    list_display = (action, 'user', 'research_group', 'node', 'slice')


class ResearchGroupAdmin(admin.ModelAdmin):
    inlines = [AuthorizedOfficialInline]


insert_inline(User, UserProfileInline)
insert_inline(User, AuthTokenInline)
insert_inline(User, TestbedPermissionInline)

admin.site.register(ResearchGroup, ResearchGroupAdmin)
admin.site.register(TestbedPermission, TestbedPermissionAdmin)
admin.site.register(AuthorizedOfficial)