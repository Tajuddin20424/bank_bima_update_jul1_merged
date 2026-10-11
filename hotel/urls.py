from django.urls import path

from . import views
from . import tran_views


urlpatterns = [

    path('',views.hotel_view,name='hotel'),

    path('save-hotel/',views.save_hotel,name='save_hotel'),

    path('update-hotel/',views.update_hotel,name='update_hotel'),

    path('load-hotel/',views.load_hotel,name='load_hotel'),

    path('delete-hotel/',views.delete_hotel,name='delete_hotel'),


    #payment--------------------------------------------

    path('payment/',tran_views.hotel_payment_list,name='hotel_payment_list'),

    path('payment-list-load/',tran_views.hotel_payment_list_load,name='hotel_payment_list_load'),
    
    path('payment/add-payment/',tran_views.add_hotel_payment_page,name='add_hotel_payment_page'),

    path('payment/save-payment/',tran_views.save_hotel_payment,name='save_hotel_payment'),
    
    path('payment/edit/<int:id>/',tran_views.edit_hotel_payment_page,name='edit_hotel_payment_page'),

    path('payment/search-guest/',tran_views.search_hotel_guest,name='search_hotel_guest'),    
    path('get-page-init-add-payment/',tran_views.get_page_init_add_payment,name='hotel_get_page_init_add_payment'),


    # ==========================================
    # FILTER COMBO
    # ==========================================

    path('filter/sr/',tran_views.hotel_filter_sr_combo,name='hotel_filter_sr_combo'),
    
    path('filter/guest/',tran_views.hotel_filter_guest_combo,name='hotel_filter_guest_combo'),

    path('filter/tran-by/',tran_views.hotel_filter_tran_by_combo,name='hotel_filter_tran_by_combo'),

    path('transaction/product-search/',tran_views.product_search,name='hotel_product_search'),


    # ==========================================
    # PARTY PAYMENT
    # ==========================================

    path('party-payment/',tran_views.hotel_party_payment_list,name='hotel_party_payment_list'),

    path('party-payment/list-load/',tran_views.hotel_party_payment_list_load,name='hotel_party_payment_list_load'),

    path('party-payment/form/<int:id>/',tran_views.hotel_party_payment_form,name='hotel_party_payment_form'),

    path('party-payment/process/<int:id>/',tran_views.process_hotel_payment,name='process_hotel_payment'),

    path('api/autocomplete/sr/', tran_views.autocomplete_sr, name='api_autocomplete_sr'),
    
    path('party-payment/preview/<int:transaction_id>/',tran_views.hotel_party_payment_preview,name='hotel_party_payment_preview'),

    
]