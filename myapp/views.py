from django.shortcuts import render,redirect
from myapp.models import (
    User, Product, Appointment, Prescription, Medicine, 
    SmartBucket, SmartBucketItem, Order, OrderItem, 
    MedicineRefill, ConditionChatMessage, HealthTip, 
    CommunityGroup, GroupMessage, GroupMember, CartItem
)
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from datetime import datetime,time, date, timedelta
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import csv
import difflib
from django.http import JsonResponse
import os
from django.views.decorators.csrf import csrf_exempt
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
# Create your views here.

def home(request):
    if not request.user.is_authenticated:
        return render(request, 'home.html') # Landing page (currently shared, maybe split later if needed but home.html handles guest)

    if request.user.is_superuser or request.user.role == 'admin':
        return render(request, 'admin_home.html')
    elif request.user.role == 'doctor':
        return render(request, 'doctor_home.html')
    else:
        # REFILL AUTO-POPULATION LOGIC
        if request.user.is_authenticated and request.user.role == 'patient':
            today = date.today()
            due_refills = MedicineRefill.objects.filter(
                patient=request.user, 
                is_active=True, 
                next_refill_date__lte=today
            )
            
            if due_refills.exists():
                for refill in due_refills:
                    product = refill.product
                    requested_qty = refill.quantity
                    
                    # Stock Validation
                    available_stock = product.stock
                    cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product)
                    current_cart_qty = 0 if created else cart_item.quantity
                    
                    total_requested = current_cart_qty + requested_qty
                    
                    final_qty = requested_qty
                    if total_requested > available_stock:
                        final_qty = max(0, available_stock - current_cart_qty)
                        if final_qty < requested_qty:
                            messages.warning(request, f"Low stock for {product.name}. Only {final_qty} units added (Limit reached).")

                    if final_qty > 0:
                        if created:
                            cart_item.quantity = final_qty
                        else:
                            cart_item.quantity += final_qty
                        cart_item.save()
                        messages.success(request, f"REFILLED: {product.name} (x{final_qty}) added to cart!")
                    
                    # Reschedule for next month
                    refill.next_refill_date = today + timedelta(days=30)
                    refill.save()

        return render(request, 'patient_home.html')

def patient_refills(request):
    if not request.user.is_authenticated or request.user.role != 'patient':
        return redirect('login')
    
    refills = MedicineRefill.objects.filter(patient=request.user, is_active=True).order_by('next_refill_date')
    return render(request, 'patient_refills.html', {'refills': refills})

def add_refill(request):
    if not request.user.is_authenticated or request.user.role != 'patient':
        return redirect('login')
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))
        
        product = Product.objects.get(id=product_id)
        # Set next refill to 30 days from now 
        next_date = date.today() + timedelta(days=30)
        
        MedicineRefill.objects.create(
            patient=request.user,
            product=product,
            quantity=quantity,
            next_refill_date=next_date
        )
        return redirect('patient_refills')
    
    products = Product.objects.filter(category='medicine')
    return render(request, 'add_refill.html', {'products': products})

def delete_refill(request, refill_id):
    if not request.user.is_authenticated or request.user.role != 'patient':
        return redirect('login')
    
    refill = MedicineRefill.objects.get(id=refill_id, patient=request.user)
    refill.is_active = False
    refill.save()
    return redirect('patient_refills')


def login_view(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            # Superuser → direct login
            if user.is_superuser:
                login(request, user)
                return redirect('home')

            # Doctor or Patient → check status
            if user.status == 'accepted':
                login(request, user)
                return redirect('home')
            else:
                context = {
                    "error": "Your account is not approved yet. Please wait for admin approval."
                }
                return render(request, "login.html", context)

        else:
            context = {"error": "Invalid email or password"}
            return render(request, "login.html", context)

    return render(request, "login.html")


def register(request):
    if request.method == "POST":
        fullname = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        role = request.POST.get("role")
        weight = request.POST.get("weight")
        height = request.POST.get("height")
        blood_type = request.POST.get("blood_type")
        age = request.POST.get("age")
        specialization = request.POST.get("specialization")
        gender = request.POST.get("gender")
        health_conditions = request.POST.get("health_conditions")
        image = request.FILES.get("image")
        id_proof = request.FILES.get("id_proof")
        experience = request.POST.get("experience")

        # 🚫 VALIDATION: Doctor must have specialization
        if role == "doctor":
            if not specialization:
                messages.error(request, "Specialization is required for doctors")
                return render(request, "register.html")
            if not id_proof:
                messages.error(request, "ID Proof is required for doctors")
                return render(request, "register.html")
            if not experience:
                messages.error(request, "Experience is required for doctors")
                return render(request, "register.html")
            
            if experience and experience.isdigit():
                experience = int(experience)
            else:
                experience = 0
        else:
            experience = 0
        
        if role == "patient":
            status = "accepted"


        if role == "doctor":
            status = "pending"

        # Create user
        user = User.objects.create_user(
            email=email,
            password=password,
            fullname=fullname,
            gender=gender,
            weight_kg=weight,
            height_cm=height,
            health_conditions=health_conditions,
            blood_type=blood_type,
            age=age,
            phone=phone,
            status=status,
            profile=image,
            id_proof=id_proof,
            role=role,
            specialization=specialization if role == "doctor" else None,
            experience=experience
        )

        messages.success(request, "Registration successful")
        return redirect("login")

    return render(request, "register.html")


def edit_profile(request):
    if request.method == "POST":
        dname = request.POST.get('dname')
        dphone = request.POST.get('dphone')
        dimage = request.FILES.get('dimage')
        dexperience = request.POST.get('dexperience')
        
        user = request.user
        user.fullname = dname
        user.phone = dphone
        
        if dimage:
            user.profile = dimage
        
        if user.role == 'doctor':
            dspecialization = request.POST.get('dspecialization')
            # dfee = request.POST.get('dfee')
            user.specialization = dspecialization
            # user.fee = dfee
            user.experience = dexperience

        elif user.role == 'patient':
            user.age = request.POST.get('age')
            user.height_cm = request.POST.get('height')
            user.weight_kg = request.POST.get('weight')
            user.health_conditions = request.POST.get('health_conditions')
            user.blood_type = request.POST.get('blood_type')
            user.gender = request.POST.get('gender')
            
        user.save()
        messages.success(request, "Profile updated successfully")
        return redirect('profile')

    template_name = 'edit_profile_mobile.html' if request.user.role == 'patient' else 'edit_profile.html'

    return render(request, template_name, {
        'specializations': User.SPECIALIZATION_CHOICES,
        'gender_choices': User.GENDER_CHOICES,
        'blood_types': User.BLOOD_CHOICES,
    })

def profile_view(request):
    if request.user.is_superuser or request.user.role == 'admin' or request.user.role == 'doctor':
        return render(request, 'profile_web.html')
    else:
        return render(request, 'profile_mobile.html')

def browse_products(request):
    products = Product.objects.all()

    # SEARCH
    search = request.GET.get('search')
    if search:
        products = products.filter(name__icontains=search)

    # FILTER BY TYPE (medicine/device/supplement)
    product_type = request.GET.get('type')
    if product_type:
        products = products.filter(category=product_type)

    # FILTER BY CONDITION
    condition = request.GET.get('condition')
    if condition:
        products = products.filter(condition=condition)

    brand = request.GET.get('brand')
    if brand:
        products = products.filter(brand__icontains=brand)

    # CHECK CONDITIONS FOR WARNINGS
    if request.user.is_authenticated and request.user.role == 'patient':
        patient_conditions = request.user.health_conditions
        patient_conditions_list = [c.strip().lower() for c in patient_conditions.split(',')] if patient_conditions else []
        for product in products:
            product.show_warning = False
            if product.allergic_to:
                product_allergies = [a.strip().lower() for a in product.allergic_to.split(',')]
                if any(any(p_allergy in cond for p_allergy in product_allergies) for cond in patient_conditions_list) or any(any(cond in p_allergy for cond in patient_conditions_list) for p_allergy in product_allergies):
                    product.show_warning = True

    # SORT: warning products appear last
    products = sorted(products, key=lambda p: getattr(p, 'show_warning', False))

    # PASS CART QUANTITIES to template
    session_cart = {}
    if request.user.is_authenticated:
        session_cart = {str(item.product_id): item.quantity for item in CartItem.objects.filter(user=request.user)}
    
    for product in products:
        pid_str = str(product.id)
        product.cart_qty = session_cart.get(pid_str, 0)

    context = {
        'products': products,
        'active_category': request.GET.get('category', 'all')
    }

    return render(request, 'browse.html', context)




def add_to_cart(request, product_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product)

        current_qty = 0 if created else cart_item.quantity
        
        # STOCK VALIDATION
        if current_qty + 1 > product.stock:
            messages.error(request, f"Sorry, only {product.stock} units of {product.name} are available in stock.")
            if created: cart_item.delete() # Cleanup if we just created it
            return redirect('browse')

        if created:
            cart_item.quantity = 1
        else:
            cart_item.quantity += 1
        
        cart_item.save()

    return redirect('browse')


def update_cart(request, product_id, action):
    if not request.user.is_authenticated:
        return redirect('login')

    pid_str = str(product_id)
    try:
        cart_item = CartItem.objects.get(user=request.user, product_id=product_id)
        
        if action == 'add':
            product = cart_item.product
            if cart_item.quantity + 1 > product.stock:
                messages.error(request, f"Cannot add more. Only {product.stock} units available.")
            else:
                cart_item.quantity += 1
                cart_item.save()
        elif action == 'remove':
            cart_item.quantity -= 1
            if cart_item.quantity <= 0:
                cart_item.delete()
            else:
                cart_item.save()
        elif action == 'delete':
            cart_item.delete()
            
    except CartItem.DoesNotExist:
        pass

    # Redirect back to where user came from
    referer = request.META.get('HTTP_REFERER', '')
    if 'cart' in referer:
        return redirect('cart')
    return redirect('browse')


def cart(request):
    if not request.user.is_authenticated:
        return redirect('login')

    items = CartItem.objects.filter(user=request.user).select_related('product')
    cart_items = []
    total = 0

    for item in items:
        subtotal = item.product.price * item.quantity
        total += subtotal
        cart_items.append({
            'id': item.product.id,
            'product': {
                'name': item.product.name,
                'price': float(item.product.price),
                'category': item.product.category,
            },
            'quantity': item.quantity,
            'subtotal': subtotal
        })

    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total': total
    })

def checkout(request):
    if not request.user.is_authenticated:
        return redirect('login')

    items = CartItem.objects.filter(user=request.user).select_related('product')
    if not items.exists():
        return redirect('browse')

    cart_items = []
    total = 0
    prescription_needed = False
    rx_product_names = []

    for item in items:
        product_obj = item.product
        is_rx = product_obj.prescription_required
        
        if is_rx:
            prescription_needed = True
            rx_product_names.append(product_obj.name.lower())

        subtotal = product_obj.price * item.quantity
        total += subtotal
        cart_items.append({
            'product': {
                'name': product_obj.name,
                'category': product_obj.category,
            },
            'quantity': item.quantity,
            'subtotal': subtotal,
            'prescription_required': is_rx,
            'image_url': product_obj.image.url if product_obj.image else None
        })

    user = request.user
    initial_data = {
        'name': user.get_full_name() or user.username,
        'email': user.email,
        'address': getattr(user,'address','') # optional field
    }

    if request.method == 'POST':
        # Here you can integrate payment
        request.session['cart'] = {}  # clear cart after order
        request.session.modified = True
        return redirect('order_success')

    return render(request, 'checkout.html',{
        'cart_items': cart_items,
        'total': total,
        'initial_data': initial_data,
        'prescription_needed': prescription_needed,
        'rx_product_names': json.dumps(rx_product_names)
    })



def payment(request):
    if not request.user.is_authenticated:
        return redirect('login')

    items = CartItem.objects.filter(user=request.user).select_related('product')
    total = sum(item.product.price * item.quantity for item in items)

    if request.method == 'POST':
        # Create Order
        order = Order.objects.create(
            user=request.user,
            total_amount=total,
            address=getattr(request.user, 'address', 'User Address'),
            status='Success'
        )
        
        # Create OrderItems & Update Stock & Clear Cart
        for item in items:
            product = item.product
            
            # DECREASE STOCK
            if product.stock >= item.quantity:
                product.stock -= item.quantity
                product.save()
            else:
                product.stock = 0
                product.save()

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item.quantity,
                price=product.price
            )
        
        # CLEAR DB CART
        items.delete()

        return redirect('order_success')

    return render(request, 'payment.html', {'total': total})



def order_success(request):
    return render(request, 'order_success.html')


def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at').prefetch_related('items__product')
    return render(request, 'orders.html', {'orders': orders})




def doctor_list(request):
    specialization = request.GET.get('specialization', 'all')

    doctors = User.objects.filter(role='doctor')

    if specialization != 'all':
        doctors = doctors.filter(specialization__iexact=specialization)

    return render(request, 'patient_doctors.html', {
        'doctors': doctors,
        'selected_specialization': specialization,
    })




from django.shortcuts import get_object_or_404







def book_appointment(request, doctor_id):
    doctor = get_object_or_404(User, id=doctor_id, role='doctor')

    # Create dictionary for patient template
    appointment = {
        'doctor': doctor,
        'date': datetime.now().strftime('%d %b %Y'),
        'time': '10:30 AM',
        'amount': getattr(doctor, 'fee', 200),  # optional fee
    }

    if request.method == 'POST':
        selected_date_str = request.POST.get('appointment_date')
        try:
            # Parse YYYY-MM-DD from HTML5 date input
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            display_date = selected_date.strftime('%d %b %Y')
        except (ValueError, TypeError):
            selected_date = datetime.now().date()
            display_date = selected_date.strftime('%d %b %Y')

        # Save appointment in the database so the doctor can see it
        Appointment.objects.create(
            doctor=doctor,
            patient=request.user,
            date=selected_date,
            time=datetime.now().time(),
            amount=getattr(doctor, 'fee', 200),
            payment_method=request.POST.get('payment'),
            status='Confirmed'
        )

        # Optional: still save in session for patient display
        appointments = request.session.get('appointments', [])
        appointments.append({
            'doctor_id': doctor.id,
            'doctor_name': doctor.fullname,
            'doctor_spec': getattr(doctor, 'specialization', 'General'),
            'date': display_date,
            'time': appointment['time'],
            'amount': float(appointment['amount']), # Fix: Decimal not JSON serializable
            'payment_method': request.POST.get('payment'),
            'status': 'Confirmed'
        })
        request.session['appointments'] = appointments

        return redirect('payment_success')

    return render(request, 'book_appointment.html', {'appointment': appointment})




def payment_success(request):
    return render(request, 'payment_success.html')


def my_appointments(request):
    # Get all appointments booked by the logged-in user
    appointments = Appointment.objects.filter(patient=request.user).order_by('-date', '-time')
    
    return render(request, 'view_my_appointments.html', {'appointments': appointments})



def upload_prescription(request):
    if request.method == "POST":
        uploaded_file = request.FILES.get('prescription_file')
        notes = request.POST.get('notes', '')

        # 1. Detect Condition
        detected_condition = "Pending Analysis"
        text = notes.lower() if notes else ""

        if text:
            if "sugar" in text or "diabetes" in text:
                detected_condition = "Diabetes"
            elif "bp" in text or "pressure" in text:
                detected_condition = "Blood Pressure"
            elif "fever" in text:
                detected_condition = "Fever"
        
        # 2. MATCH MEDICINES & AUTO-ADD TO CART
        added_medicines = []
        if text:
            # Fetch all medicines
            medicines = Product.objects.all()
            
            cart = request.session.get('cart', {})
            # Sanitize cart
            for k, v in list(cart.items()):
                if isinstance(v, int): del cart[k]

            # Tokenize and Clean text for robust matching
            import re
            tokens = re.findall(r'\b\w+\b', text.lower())
            clean_text = re.sub(r'[^a-z0-9]', '', text.lower())

            # Define frequency multipliers
            FREQ_MAP = {
                'qd': 1, 'once': 1, 'daily': 1,
                'bid': 2, 'twice': 2,
                'tid': 3, 'thrice': 3,
                'qid': 4, 'four': 4
            }

            for med in medicines:
                med_name_lower = med.name.lower()
                clean_med_name = re.sub(r'[^a-z0-9]', '', med_name_lower)
                
                is_match = False
                match_pos = -1
                
                # Check 1: Strict substring match
                if med_name_lower in text.lower():
                    is_match = True
                    match_pos = text.lower().find(med_name_lower)
                
                # Check 2: Normalized match (ignore spaces/punctuation)
                elif clean_med_name in clean_text:
                    is_match = True
                    # for context, we still try to find something similar in the raw text
                    match_pos = text.lower().find(med_name_lower[:3]) # approximate

                # Check 3: Fuzzy match tokens (tolerant of typos like "Cimelidine")
                elif tokens:
                    matches = difflib.get_close_matches(med_name_lower, tokens, n=1, cutoff=0.7)
                    if matches:
                        is_match = True
                        match_pos = text.lower().find(matches[0])

                if is_match:
                    # DOSAGE CALCULATION
                    qty = 1
                    if match_pos != -1:
                        # Extract ~60 chars of context after the medicine name
                        context = text[match_pos + len(med_name_lower):match_pos + len(med_name_lower) + 60].lower()
                        
                        # Pattern A: "1 for 14 day"
                        simple_for = re.search(r"(\d+)\s+for\s+(\d+)\s+days?", context)
                        if simple_for:
                            qty = int(simple_for.group(1)) * int(simple_for.group(2))
                        else:
                            # Pattern B: "1 tab BID for 10 days" or "1 tab TID"
                            # Match pills, optional unit, frequency word, optional duration
                            dosage = re.search(r"(\d+)\s*(?:tabs?|caps?|pills?|mg)?\s*(bid|tid|qid|qd|once|twice|thrice)?.*?(\d+)?\s*days?", context)
                            if dosage:
                                pills = int(dosage.group(1))
                                freq_word = dosage.group(2)
                                days_val = dosage.group(3)
                                
                                freq = FREQ_MAP.get(freq_word, 1)
                                days = int(days_val) if days_val else 1
                                qty = pills * freq * days
                                # Safety: if qty still 1 but we found pills, use pills
                                if qty == 1 and pills > 1: qty = pills

                    pid_str = str(med.id)
                    
                    # STOCK VALIDATION
                    available_stock = med.stock
                    cart_item, created = CartItem.objects.get_or_create(user=request.user, product=med)
                    current_cart_qty = 0 if created else cart_item.quantity
                    total_requested = current_cart_qty + qty
                    
                    final_qty = qty
                    if total_requested > available_stock:
                        final_qty = max(0, available_stock - current_cart_qty)
                        if final_qty < qty:
                            messages.warning(request, f"Low stock for {med.name}. Only {final_qty} units added (Limit reached).")

                    if final_qty > 0:
                        if created:
                            cart_item.quantity = final_qty
                        else:
                            cart_item.quantity += final_qty
                        cart_item.save()
                        added_medicines.append(f"{med.name} (x{final_qty})")
                    elif not created:
                        # If we didn't add anything but item existed, keep it (don't delete)
                        pass
                    elif created:
                        # If we just created but couldn't add any quantity, cleanup
                        cart_item.delete()
            
            if added_medicines:
                request.session['cart'] = cart
                request.session.modified = True
                messages.success(request, f"Automatically added to cart: {', '.join(added_medicines)}")


        # 3. Save Prescription
        Prescription.objects.create(
            patient=request.user,                 
            uploaded_file=uploaded_file,          
            notes=notes,
            detected_condition=detected_condition 
        )

        return redirect('patient_prescriptions')

    return render(request, 'upload.html')



def upload_success(request):
    return render(request, 'upload_success.html')




def logout_view(request):
    logout(request)
    return redirect('login')




def doctor_appointments_view(request):
    if request.user.role != 'doctor':
        return redirect('home')

    appointments = Appointment.objects.filter(doctor=request.user).order_by('-date', '-time')

    return render(request, 'doctor_appointments.html', {
        'appointments': appointments
    })

def doctor_prescriptions_view(request):
    if request.user.role != 'doctor':
        return redirect('home')

    prescriptions = Prescription.objects.filter(doctor=request.user).order_by('-date')

    return render(request, 'doctor_prescriptions.html', {'prescriptions': prescriptions})

def stock_report(request):
    # Fetch all products from DB
    products = Product.objects.all().order_by('-id')

    # Optional: Add search/filter like browse page
    search = request.GET.get('search')
    if search:
        products = products.filter(name__icontains=search)

    product_type = request.GET.get('type')
    if product_type:
        products = products.filter(category=product_type)

    condition = request.GET.get('condition')
    if condition:
        products = products.filter(condition=condition)

    brand = request.GET.get('brand')
    if brand:
        products = products.filter(brand__icontains=brand)

    return render(request, 'stock_report.html', {
        'stock_items': products,
    })


def add_product(request):
    # Admin only
    if not request.user.is_superuser and request.user.role != 'admin':
        return redirect('home')

    if request.method == "POST":
        name = request.POST.get('name')
        brand = request.POST.get('brand')
        category = request.POST.get('category')
        condition = request.POST.get('condition')
        allergic_to = request.POST.get('allergic_to')
        prescription_required = request.POST.get('prescription_required') == 'on'
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        image = request.FILES.get('image')

        Product.objects.create(
            name=name,
            brand=brand,
            category=category,
            condition=condition,
            allergic_to=allergic_to,
            prescription_required=prescription_required,
            price=price,
            stock=stock,
            image=image
        )
        
        messages.success(request, "Product added successfully")
        return redirect('stock_report')

    return render(request, 'add_product.html')


def edit_product(request, product_id):
    if not request.user.is_superuser and request.user.role != 'admin':
        return redirect('home')

    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        product.name = request.POST.get('name')
        product.brand = request.POST.get('brand')
        product.category = request.POST.get('category')
        product.condition = request.POST.get('condition')
        product.allergic_to = request.POST.get('allergic_to')
        product.prescription_required = request.POST.get('prescription_required') == 'on'
        product.price = request.POST.get('price')
        product.stock = request.POST.get('stock')
        if request.FILES.get('image'):
            product.image = request.FILES.get('image')
        product.save()
        messages.success(request, "Product updated successfully")
        return redirect('stock_report')

    return render(request, 'edit_product.html', {'product': product})


def delete_product(request, product_id):
    if not request.user.is_superuser and request.user.role != 'admin':
        return redirect('home')

    product = get_object_or_404(Product, id=product_id)
    if request.method == "POST":
        product.delete()
        messages.success(request, "Product deleted successfully")
        return redirect('stock_report')

    return redirect('stock_report')



def consultation_report(request):

    # Allow only admin/superuser
    if not request.user.is_superuser and request.user.role != 'admin':
        return redirect('home')

    appointments = Appointment.objects.select_related(
        'doctor', 'patient'
    ).order_by('-date', '-time')

    return render(request, 'consultation_report.html', {
        'appointments': appointments
    })


def patient_details(request):
    # only patients
    patients = User.objects.filter(role='patient')

    return render(request, 'patient_details.html', {
        'patients': patients
    })


def delete_patient(request, patient_id):
    patient = get_object_or_404(User, id=patient_id, role='patient')

    if request.method == "POST":
        patient.delete()
        messages.success(request, "Patient deleted successfully")
        return redirect('patient_details')

    return redirect('patient_details')


def doctor_details(request):
    doctors = User.objects.filter(role='doctor')
    return render(request, 'admin_doctors.html', {
        'doctors': doctors
    })



def delete_doctor(request, doctor_id):
    if request.method == 'POST':
        try:
            doctor = User.objects.get(id=doctor_id, role='doctor')
            doctor.delete()
        except User.DoesNotExist:
            pass
    return redirect('doctor_details')


def patient_prescriptions(request):
    if request.user.role != 'patient':
        return redirect('home')

    prescriptions = Prescription.objects.filter(patient=request.user).order_by('-id')
    return render(request, 'patient_prescriptions.html', {
        'prescriptions': prescriptions
    })

# def admin_prescriptions(request):
#     if request.user.role != 'admin' and not request.user.is_superuser:
#         return redirect('home')

#     prescriptions = Prescription.objects.all()
#     return render(request, 'admin_prescriptions.html', {'prescriptions': prescriptions})


# def verify_prescription(request, pid):
#     if request.user.role != 'admin' and not request.user.is_superuser:
#         return redirect('home')

#     prescription = Prescription.objects.get(id=pid)
#     prescription.verified = True  # add a BooleanField verified=True in Prescription
#     prescription.save()

#     return redirect('admin_prescriptions')


def doctor_create_prescription(request):
    if request.user.role != 'doctor':
        messages.error(request, "Only doctors can create prescriptions.")
        return redirect('home')

    patients = User.objects.filter(role='patient')

    if request.method == 'POST':
        patient_id = request.POST.get('patient')
        notes = request.POST.get('notes')
        uploaded_file = request.FILES.get('uploaded_file')  # optional

        patient = get_object_or_404(User, id=patient_id, role='patient')

        Prescription.objects.create(
            doctor=request.user,
            patient=patient,
            notes=notes,
            uploaded_file=uploaded_file,
            verified=True  # doctor-created prescriptions can be auto-verified
        )

        messages.success(request, f"Prescription created for {patient.fullname}.")
        return redirect('doctor_prescriptions')

    return render(request, 'doctor_create_prescription.html', {'patients': patients})


def doctor_prescriptions(request):
    if request.user.role != 'doctor':
        return redirect('home')

    prescriptions = Prescription.objects.filter(doctor=request.user)
    return render(request, 'doctor_prescriptions.html', {'prescriptions': prescriptions})


def detect_condition_from_text(text):
    text = text.lower()

    if 'diabetes' in text or 'sugar' in text or 'hba1c' in text:
        return 'Diabetes'

    if 'bp' in text or 'hypertension' in text:
        return 'Blood Pressure'

    if 'asthma' in text or 'inhaler' in text:
        return 'Asthma'

    if 'heart' in text or 'ecg' in text or 'cardiac' in text:
        return 'Heart Condition'

    if 'thyroid' in text:
        return 'Thyroid'

    return 'General / Unknown'


def condition_chat(request):
    # get latest prescription of logged-in user
    prescription = Prescription.objects.filter(
        patient=request.user
    ).order_by('-date').first()

    if not prescription or not prescription.detected_condition:
        return render(request, 'chat_not_allowed.html')

    condition = prescription.detected_condition

    # handle message send
    if request.method == "POST":
        msg = request.POST.get('message')
        if msg:
            ConditionChatMessage.objects.create(
                condition=condition,
                sender=request.user,
                message=msg
            )

    messages = ConditionChatMessage.objects.filter(
        condition=condition
    ).order_by('timestamp')

    return render(request, 'condition_chat.html', {
        'condition': condition,
        'chat_messages': messages
    })


def health_tips(request):

    HEALTH_TIPS = {
    "Diabetes": [
        "Avoid sugary foods and drinks.",
        "Exercise regularly to maintain blood sugar levels.",
        "Monitor your blood sugar daily.",
        "Stay hydrated and maintain a balanced diet."
    ],
    "Blood Pressure": [
        "Reduce salt intake in meals.",
        "Exercise at least 30 minutes a day.",
        "Avoid stress and practice relaxation.",
        "Monitor your blood pressure regularly."
    ],
    "Fever": [
        "Rest and drink plenty of fluids.",
        "Keep yourself hydrated and eat light meals.",
        "Monitor your temperature regularly.",
        "Consult a doctor if fever persists for more than 3 days."
    ]
}

    # Get the user's last uploaded prescription
    prescription = Prescription.objects.filter(
        patient=request.user
    ).order_by('-date').first()

    if not prescription or not prescription.detected_condition:
        tips = []
        condition = None
    else:
        condition = prescription.detected_condition
        tips = HEALTH_TIPS.get(condition, [])

    return render(request, 'health_tips.html', {
        'condition': condition,
        'tips': tips
    })


def delete_prescription(request, prescription_id):
    # Only allow the owner to delete
    prescription = get_object_or_404(Prescription, id=prescription_id, patient=request.user)
    
    # Delete the uploaded file from storage first (optional)
    if prescription.uploaded_file:
        prescription.uploaded_file.delete(save=False)
    
    # Delete the prescription record
    prescription.delete()
    
    return redirect('patient_prescriptions')


from django.utils import timezone
from datetime import timedelta


def admin_orders(request):
    if not request.user.is_superuser and request.user.role != 'admin':
        return redirect('home')
    
    orders = Order.objects.all().order_by('-created_at').prefetch_related('items__product')
    return render(request, 'admin_orders.html', {'orders': orders})


def reminders(request):
    # Assume each prescription lasts 30 days
    MEDICINE_DURATION_DAYS = 30
    REMINDER_BEFORE_DAYS = 5  # show reminder 5 days before completion

    # Get the last prescription of the user
    last_prescription = Prescription.objects.filter(
        patient=request.user
    ).order_by('-date').first()

    reminder_message = None

    if last_prescription:
        last_date = last_prescription.date
        days_since = (timezone.now().date() - last_date).days
        days_left = MEDICINE_DURATION_DAYS - days_since

        # Show reminder if medicine is about to finish
        if 0 < days_left <= REMINDER_BEFORE_DAYS:
            reminder_message = f"Your medicine will finish in {days_left} day(s). Consider restocking it."

    return render(request, 'reminders.html', {
        'reminder_message': reminder_message,
        'last_prescription': last_prescription
    })


def browse_doctors(request):
    selected_specialization = request.GET.get('specialization')

    # Only doctors
    doctors = User.objects.filter(role='doctor', status='active')

    # Filter by specialization if selected
    if selected_specialization:
        doctors = doctors.filter(specialization=selected_specialization)

    # Get specialization choices directly from model
    specializations = User.SPECIALIZATION_CHOICES

    return render(request, 'browse_doctors.html', {
        'doctors': doctors,
        'specializations': specializations,
        'selected_specialization': selected_specialization,
    })



from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from .models import CommunityGroup, GroupMessage, GroupMember

@login_required
def group_list(request):
    # Show all groups
    groups = CommunityGroup.objects.all()
    # Check which groups user has joined
    joined_group_ids = GroupMember.objects.filter(user=request.user).values_list('group_id', flat=True)
    
    if request.user.is_superuser or request.user.role == 'admin' or request.user.role == 'doctor':
        template = 'group_list_web.html'
    else:
        template = 'group_list_mobile.html'

    return render(request, template, {
        'groups': groups,
        'joined_group_ids': joined_group_ids
    })

@login_required
def join_group(request, group_id):
    group = get_object_or_404(CommunityGroup, id=group_id)
    GroupMember.objects.get_or_create(group=group, user=request.user)
    return redirect('group_chat', group_id=group.id)

@login_required
def leave_group(request, group_id):
    group = get_object_or_404(CommunityGroup, id=group_id)
    GroupMember.objects.filter(group=group, user=request.user).delete()
    return redirect('group_list')

@login_required
def group_chat(request, group_id):
    group = get_object_or_404(CommunityGroup, id=group_id)

    # Admin/staff can view all chats
    if not GroupMember.objects.filter(group=group, user=request.user).exists() and not request.user.is_staff:
        # non-members cannot view
        return redirect('group_list')

    messages = GroupMessage.objects.filter(group=group).order_by('timestamp')

    if request.method == 'POST':
        msg = request.POST.get('message')
        if msg:
            GroupMessage.objects.create(group=group, user=request.user, message=msg)
        return redirect('group_chat', group_id=group.id)

    template = 'group_chat_mobile.html'
    if request.user.is_superuser or request.user.role == 'admin' or request.user.role == 'doctor':
        template = 'group_chat_web.html'

    return render(request, template, {
        'group': group,
        'chat_messages': messages,
        'is_admin': request.user.is_staff
    })

# OPTIONAL: Admin custom page (header option)

@staff_member_required
def admin_group_manage(request):
    groups = CommunityGroup.objects.all()
    users = User.objects.all()

    if request.method == "POST":
        name = request.POST.get("name")
        desc = request.POST.get("description")
        if name:
            CommunityGroup.objects.create(
                name=name,
                description=desc,
                created_by=request.user
            )
            return redirect("admin_group_manage")

    return render(request, "admin_group_manage.html", {
        "groups": groups,
        "users": users
    })


@staff_member_required
def delete_message(request, msg_id):
    msg = get_object_or_404(GroupMessage, id=msg_id)
    group_id = msg.group.id
    msg.delete()
    return redirect('group_chat', group_id=group_id)


@staff_member_required
def remove_member(request, member_id):
    GroupMember.objects.filter(id=member_id).delete()
    return redirect('admin_group_manage')










def accept_doctor(request, doctor_id):
    doctor = get_object_or_404(User, id=doctor_id)
    doctor.status = 'accepted'
    doctor.save()
    return redirect('doctor_details')


def reject_doctor(request, doctor_id):
    doctor = get_object_or_404(User, id=doctor_id)
    doctor.status = 'rejected'
    doctor.save()
    return redirect('doctor_details')



def load_chatbot_data():
    questions = []
    answers = []
    # Make sure 'dataset/patient_medicine.csv' exists in your project root or adjust path
    csv_path = os.path.join(settings.BASE_DIR, 'dataset', 'patient_medicine.csv')
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader) # skip header
            for row in reader:
                if len(row) >= 2:
                    questions.append(row[0])
                    answers.append(row[1])
    except Exception as e:
        print(f"Error loading chatbot CSV: {e}")
        
    return questions, answers


# Load data once (Global variable)
CHAT_QUESTIONS, CHAT_ANSWERS = load_chatbot_data()

# Initialize Vectorizer
vectorizer = TfidfVectorizer().fit(CHAT_QUESTIONS)
tfidf_matrix = vectorizer.transform(CHAT_QUESTIONS)


def chatbot_view(request):
    return render(request, 'chatbot.html')


@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_msg = data.get('message', '').strip()
            
            if not user_msg:
                return JsonResponse({'response': "Please say something!"})

            # Transform user message
            user_vec = vectorizer.transform([user_msg])
            
            # Calculate Cosine Similarity
            similarities = cosine_similarity(user_vec, tfidf_matrix)
            
            # Find best match
            best_match_idx = np.argmax(similarities)
            best_score = similarities[0][best_match_idx]
            
            if best_score > 0.3: # Threshold 
                response_text = CHAT_ANSWERS[best_match_idx]
            else:
                response_text = "I'm not sure about that. Please describe your symptoms in more detail or consult a doctor."

            # --- AUTO-ADD MEDICINE TO CART LOGIC ---
            added_info = None
            if request.user.is_authenticated and request.user.role == 'patient':
                import re
                products = Product.objects.all()
                
                for product in products:
                    if re.search(rf"\b{re.escape(product.name)}\b", response_text, re.IGNORECASE):
                        # Stock Validation
                        available_stock = product.stock
                        cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product)
                        current_cart_qty = 0 if created else cart_item.quantity
                        
                        if current_cart_qty < available_stock:
                            if created:
                                cart_item.quantity = 1
                            else:
                                cart_item.quantity += 1
                            cart_item.save()
                            added_info = f"{product.name} (x1) has been added to your cart!"
                            break 
                        elif created:
                            cart_item.delete()

            return JsonResponse({
                'response': response_text,
                'added_info': added_info
            })
        
        except Exception as e:
            print(f"Chatbot Error: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'response': f"Debug Error: {str(e)}"}, status=200)
    return JsonResponse({'error': 'Invalid request'}, status=400)


def nearby_map(request):
    return render(request, 'nearby_map.html')


# ================= SMART BUCKET (ADMIN) =================

def admin_smart_buckets(request):
    if not request.user.is_superuser and request.user.role != 'admin':
        return redirect('home')
    
    buckets = SmartBucket.objects.all().order_by('-created_at')
    return render(request, 'admin_smart_buckets.html', {'buckets': buckets})

def add_smart_bucket(request):
    if not request.user.is_superuser and request.user.role != 'admin':
        return redirect('home')
    
    products = Product.objects.all()

    if request.method == "POST":
        name = request.POST.get('name')
        description = request.POST.get('description')
        image = request.FILES.get('image')

        bucket = SmartBucket.objects.create(
            name=name,
            description=description,
            image=image
        )

        # Dynamic items
        product_ids = request.POST.getlist('product_id')
        quantities = request.POST.getlist('quantity')

        for pid, qty in zip(product_ids, quantities):
            if pid and qty:
                prod = Product.objects.get(id=pid)
                SmartBucketItem.objects.create(
                    bucket=bucket,
                    product=prod,
                    quantity=int(qty)
                )
        
        messages.success(request, "Smart Bucket created successfully")
        return redirect('admin_smart_buckets')

    return render(request, 'add_smart_bucket.html', {'products': products})

def edit_smart_bucket(request, bucket_id):
    if not request.user.is_superuser and request.user.role != 'admin':
        return redirect('home')
    
    bucket = get_object_or_404(SmartBucket, id=bucket_id)
    products = Product.objects.all()

    if request.method == "POST":
        bucket.name = request.POST.get('name')
        bucket.description = request.POST.get('description')
        if request.FILES.get('image'):
            bucket.image = request.FILES.get('image')
        bucket.save()

        # Update items: Clear and Re-add (simplest for dynamic rows)
        bucket.bucket_items.all().delete()
        
        product_ids = request.POST.getlist('product_id')
        quantities = request.POST.getlist('quantity')

        for pid, qty in zip(product_ids, quantities):
            if pid and qty:
                prod = Product.objects.get(id=pid)
                SmartBucketItem.objects.create(
                    bucket=bucket,
                    product=prod,
                    quantity=int(qty)
                )
        
        messages.success(request, "Smart Bucket updated successfully")
        return redirect('admin_smart_buckets')

    return render(request, 'edit_smart_bucket.html', {
        'bucket': bucket,
        'products': products
    })

def delete_smart_bucket(request, bucket_id):
    if not request.user.is_superuser and request.user.role != 'admin':
        return redirect('home')
    
    bucket = get_object_or_404(SmartBucket, id=bucket_id)
    if request.method == "POST":
        bucket.delete()
        messages.success(request, "Bucket deleted successfully")
    return redirect('admin_smart_buckets')


# ================= SMART BUCKET (PATIENT) =================

def patient_buckets(request):
    buckets = SmartBucket.objects.all().order_by('-created_at')
    return render(request, 'patient_buckets.html', {'buckets': buckets})

def add_bucket_to_cart(request, bucket_id):
    if not request.user.is_authenticated:
        return redirect('login')
        
    bucket = get_object_or_404(SmartBucket, id=bucket_id)

    for item in bucket.bucket_items.all():
        cart_item, created = CartItem.objects.get_or_create(user=request.user, product=item.product)
        if created:
            cart_item.quantity = item.quantity
        else:
            cart_item.quantity += item.quantity
        cart_item.save()
    
    messages.success(request, f"Added {bucket.name} items to cart")
    return redirect('cart')
