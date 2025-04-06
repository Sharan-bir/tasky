from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Company, Domain, UserInfo
from django.utils.translation import gettext_lazy as _

class UserInfoInline(admin.StackedInline):
    model = UserInfo
    can_delete = False
    extra = 1  # Number of empty forms to display

class DomainAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'is_active')

    def company_name(self, obj):
        return obj.company.name

    company_name.short_description = 'Company Name'

class CustomUserAdmin(UserAdmin):
    inlines = [UserInfoInline]

    list_display = ('email', 'company', 'get_first_name', 'get_role', 'get_domain')
    search_fields = ('email',)
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Company Info', {'fields': ('company','role','domain')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Customize add_fieldsets for adding new users
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'company', 'role','domain', 'password1', 'password2'),  
        }),
    )


    def get_first_name(self, obj):
        return obj.info.first_name if hasattr(obj, 'info') else ''
    get_first_name.short_description = 'First Name'

    # Custom method to display role
    def get_role(self, obj):
        return obj.get_role_display() if obj.role else 'N/A'
    get_role.short_description = 'Role'

    # Custom method to display domain name
    def get_domain(self, obj):
        return obj.domain if obj.domain else 'N/A'
    get_domain.short_description = 'Domain'

# admin.site.register(User)
admin.site.register(Domain, DomainAdmin)
admin.site.register(Company)
admin.site.register(User, CustomUserAdmin)