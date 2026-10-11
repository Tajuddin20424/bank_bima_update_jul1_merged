from django.urls import path
from . import views

urlpatterns = [

    # Pages
    path('', views.bed_info_list, name='bed_info_list'),
    path('add/', views.bed_info_add, name='bed_info_add'),
    path('edit/<int:id>/', views.bed_info_edit, name='bed_info_edit'),

    path('get/', views.get_bed_info, name='get_bed_info'),
    path('save/', views.save_bed_info, name='save_bed_info'),
    path('update/', views.update_bed_info, name='update_bed_info'),
    path('remove/', views.remove_bed_info, name='remove_bed_info'),

]