from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('',views.login_view, name='login'),
    path('home/', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile_view, name='profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('browse/',views.browse_products, name='browse'),
    path('add-to-cart/<int:product_id>/',views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart, name='cart'),
    path('update-cart/<str:product_id>/<str:action>/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('payment/', views.payment, name='payment'),
    path('order-success/', views.order_success, name='order_success'),
    path('orders/', views.my_orders, name='my_orders'),
    path('doctors/', views.doctor_list, name='doctor_list'),
    path('book-appointment/<int:doctor_id>/', views.book_appointment, name='book_appointment'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('my-appointments/', views.my_appointments, name='my_appointments'),
    path('upload/', views.upload_prescription, name='upload_prescription'),
    path('prescription/patient/', views.patient_prescriptions, name='patient_prescriptions'),
    # path('prescription/admin/', views.admin_prescriptions, name='admin_prescriptions'),
    # path('prescription/verify/<int:pid>/', views.verify_prescription, name='verify_prescription'),
    path('prescription/doctor/create/', views.doctor_create_prescription, name='doctor_create_prescription'),
    path('prescription/doctor/', views.doctor_prescriptions, name='doctor_prescriptions'),
    path('upload/success/', views.upload_success, name='upload_success'),
    path('logout/', views.logout_view, name='logout'),
    path('doctor/appointments/', views.doctor_appointments_view, name='doctor_appointments'),
    path('doctor/prescriptions/', views.doctor_prescriptions_view, name='doctor_prescriptions'),
    path('admin-panel/stock-report/', views.stock_report, name='stock_report'),
    path('admin-panel/add-product/', views.add_product, name='add_product'),
    path('admin-panel/edit-product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('admin-panel/delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('admin-panel/consultation-report/',views.consultation_report,name='consultation_report'),
    path('admin-panel/patient-details/', views.patient_details, name='patient_details'),
    path('admin-panel/patient-delete/<int:patient_id>/', views.delete_patient, name='delete_patient'),
    path('admin-panel/doctors/', views.doctor_details, name='doctor_details'),
    path('admin-panel/doctor-delete/<int:doctor_id>/', views.delete_doctor, name='delete_doctor'),
    path('admin-panel/orders/', views.admin_orders, name='admin_orders'),
    path('condition-chat/', views.condition_chat, name='condition_chat'),
    path('health-tips/', views.health_tips, name='health_tips'),
    path('delete-prescription/<int:prescription_id>/', views.delete_prescription, name='delete_prescription'),
    path('reminders/', views.reminders, name='reminders'),
    path('browse-doctors/', views.browse_doctors, name='browse_doctors'),
    path('groups/', views.group_list, name='group_list'),
    path('groups/join/<int:group_id>/', views.join_group, name='join_group'),
    path('groups/leave/<int:group_id>/', views.leave_group, name='leave_group'),
    path('groups/<int:group_id>/', views.group_chat, name='group_chat'),
    path("admin-community-groups/", views.admin_group_manage, name="admin_group_manage"),
    path('groups/message/delete/<int:msg_id>/', views.delete_message, name='delete_message'),
    path('admin/groups/member/remove/<int:member_id>/', views.remove_member, name='remove_member'),

    path('accept/<int:doctor_id>/', views.accept_doctor, name='accept'),
    path('reject/<int:doctor_id>/', views.reject_doctor, name='reject'),


    path('chatbot/', views.chatbot_view, name='chatbot'),
    path('api/chat/', views.chat_api, name='chat_api'),
    path('nearby-map/', views.nearby_map, name='nearby_map'),

    # Smart Bucket (Admin)
    path('admin-panel/smart-buckets/', views.admin_smart_buckets, name='admin_smart_buckets'),
    path('admin-panel/smart-buckets/add/', views.add_smart_bucket, name='add_smart_bucket'),
    path('admin-panel/smart-buckets/<int:bucket_id>/edit/', views.edit_smart_bucket, name='edit_smart_bucket'),
    path('admin-panel/smart-buckets/<int:bucket_id>/delete/', views.delete_smart_bucket, name='delete_smart_bucket'),

    # Smart Bucket (Patient)
    path('smart-kits/', views.patient_buckets, name='patient_buckets'),
    path('add-bucket-to-cart/<int:bucket_id>/', views.add_bucket_to_cart, name='add_bucket_to_cart'),

    # Refills
    path('refills/', views.patient_refills, name='patient_refills'),
    path('refills/add/', views.add_refill, name='add_refill'),
    path('refills/delete/<int:refill_id>/', views.delete_refill, name='delete_refill'),

















]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
