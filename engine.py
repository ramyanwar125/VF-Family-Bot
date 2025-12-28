import requests

def get_flex_amount(owner_number, owner_password):
    try:
        session = requests.Session()
        
        # --- مرحلة تسجيل الدخول وجلب التوكن ---
        login_url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
        login_payload = {
            'username': owner_number,
            'password': owner_password,
            'grant_type': 'password',
            'client_secret': 'a2ec6fff-0b7f-4aa4-a733-96ceae5c84c3',
            'client_id': 'my-vodafone-app'
        }
        login_headers = {
            'User-Agent': 'okhttp/4.9.3',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip',
            'x-agent-operatingsystem': 'V12.5.13.0.RJQMIXM',
            'clientId': 'xxx',
            'x-agent-device': 'lime',
            'x-agent-version': '2024.10.1',
            'x-agent-build': '562'
        }
        
        login_response = session.post(login_url, data=login_payload, headers=login_headers, timeout=30)
        
        if login_response.status_code != 200:
            return False, 0, "❌ فشل في الاتصال بالسيرفر أو بيانات الدخول خاطئة"
            
        login_data = login_response.json()
        access_token = login_data.get('access_token')
        
        if not access_token:
            return False, 0, "❌ لم يتم العثور على صلاحية الوصول (Token)"
        
        # --- مرحلة جلب بيانات الاستهلاك (Money Back / Flex Amount) ---
        flex_url = f'https://web.vodafone.com.eg/services/dxl/usage/usageConsumptionReport?bucket.product.publicIdentifier={owner_number}&@type=aggregated'
        flex_headers = {
            'channel': 'MOBILE',
            'useCase': 'Promo',
            'Authorization': f'Bearer {access_token}',
            'api-version': 'v2',
            'x-agent-operatingsystem': '11',
            'clientId': 'AnaVodafoneAndroid',
            'x-agent-device': 'OPPO CPH2059',
            'x-agent-version': '2024.3.3',
            'x-agent-build': '593',
            'msisdn': owner_number,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Accept-Language': 'ar',
            'User-Agent': 'okhttp/4.11.0'
        }
        
        response = session.get(flex_url, headers=flex_headers, timeout=30)
        
        if response.status_code != 200:
            return False, 0, "❌ فشل في جلب رصيد الاسترداد"
        
        flex_data = response.json()
        
        # استخدام دالة الاستخراج المحدثة لضمان الحصول على القيمة
        amount = extract_money_amount(flex_data)
        
        return True, amount, "✅ تم تحديث البيانات بنجاح"
            
    except Exception as e:
        return False, 0, f"⚠️ حدث خطأ تقني: {str(e)}"

def extract_money_amount(flex_data):
    """دالة محسنة للبحث داخل الـ JSON المعقد الخاص بفودافون"""
    try:
        if not isinstance(flex_data, list):
            return 0
            
        for item in flex_data:
            # البحث عن قسم OTHERS وهو المكان الافتراضي لرصيد الـ Money Back
            if item.get('@type') == 'OTHERS' or item.get('usageType') == 'money':
                buckets = item.get('bucket', [])
                for bucket in buckets:
                    # التحقق من أن نوع الاستخدام هو "مالي"
                    if bucket.get('usageType') == 'money':
                        balances = bucket.get('bucketBalance', [])
                        for balance in balances:
                            # البحث عن القيمة المتبقية (Remaining)
                            if balance.get('@type') == 'Remaining':
                                value_info = balance.get('remainingValue', {})
                                return value_info.get('amount', 0)
        return 0
    except:
        return 0

def main():
    print("--- Vodafone Flex Check System ---")
    while True:
        num = input("الرجاء إدخال رقم الهاتف (01xxxxxxxxx): ").strip()
        if len(num) == 11 and num.isdigit():
            break
        print("⚠️ رقم غير صحيح، حاول مرة أخرى.")
    
    pwd = input("الرجاء إدخال كلمة المرور: ").strip()
    
    print("\n🔄 جاري الفحص...")
    success, amount, message = get_flex_amount(num, pwd)
    
    if success:
        print("-" * 30)
        print(f"💰 رصيد الماني باك: {amount} جنيه")
        print(f"ℹ️ الحالة: {message}")
        print("-" * 30)
    else:
        print(f"\n{message}")

if __name__ == "__main__":
    main()
