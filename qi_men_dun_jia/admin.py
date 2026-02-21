from django.contrib import admin
from qi_men_dun_jia.models import QimenCalculation, QimenPalace

class QimenPalaceInline(admin.TabularInline):
    model = QimenPalace
    extra = 0
    fields = ('index', 'gate', 'star', 'god', 'tip')

@admin.register(QimenCalculation)
class QimenCalculationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'datetime_str', 'location', 'topic', 'solar', 'parsed_datetime', 'seed', 'analysis_provider', 'analysis_model', 'analysis_time', 'created_time')
    search_fields = ('user__username', 'location', 'topic')
    inlines = [QimenPalaceInline]
