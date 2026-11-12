from django.contrib import admin

from .models import Application, Candidate, CandidateUnlock, Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'location', 'status', 'plan', 'posted_by', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('title', 'location')


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'city', 'area', 'experience', 'available_in_database')
    search_fields = ('name', 'role', 'city', 'phone')
    list_filter = ('available_in_database',)


admin.site.register(Application)
admin.site.register(CandidateUnlock)
