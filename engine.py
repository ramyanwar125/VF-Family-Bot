import requests

# القواميس الأساسية
FLEX_PACKAGES = {
    "637": "فليكس 300", "523": "فليكس 260", "636": "فليكس 150",
    "517": "فليكس 130", "516": "فليكس 100", "522": "فليكس 90",
    "515": "فليكس 70", "514": "فليكس 60", "632": "فليكس 45", "631": "فليكس 40",
}

def get_token(num, pwd):
    url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
    payload = {
        'username': num, 'password': pwd, 'grant_type': 'password',
        'client_secret': 'a2ec6fff-0b7f-4aa4-a733-96ceae5c84c3', 'client_id': 'my-vodafone-app'
    }
    headers = {
        'User-Agent': 'okhttp/4.9.3', 'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip', 'x-agent-operatingsystem': 'V12.5.13.0.RJQMIXM',
        'clientId': 'xxx', 'x-agent-device': 'lime', 'x-agent-version': '2024.10.1', 'x-agent-build': '562'
    }
    res = requests.post(url, data=payload, headers=headers, timeout=30)
    if res.status_code == 200:
        return res.json().get('access_token')
    raise Exception("❌ فشل تسجيل الدخول، تأكد من البيانات")

def run_money_back(num, token, mode='SCAN'):
    """دالة الفحص المحدثة بدون حذف أي هيدرز كما طلبت"""
    headers = {
        'channel': 'MOBILE',
        'useCase': 'Promo',
        'Authorization': f'Bearer {token}',
        'api-version': 'v2',
        'x-agent-operatingsystem': '11',
        'clientId': 'AnaVodafoneAndroid',
        'x-agent-device': 'OPPO CPH2059',
        'x-agent-version': '2024.3.3',
        'x-agent-build': '593',
        'msisdn': num,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Accept-Language': 'ar',
        'User-Agent': 'okhttp/4.11.0'
    }

    if mode == 'SCAN':
        url = f'https://web.vodafone.com.eg/services/dxl/usage/usageConsumptionReport?bucket.product.publicIdentifier={num}&@type=aggregated'
        res = requests.get(url, headers=headers, timeout=30)
        if res.status_code == 200:
            return extract_money_amount(res.json())
        return 0
    
    elif mode == 'REFUND_LIST':
        url = f"https://web.vodafone.com.eg/services/dxl/usagemng/usage?relatedParty.id={num}&@type=BalanceDetails"
        res = requests.get(url, headers=headers, timeout=30)
        offers = []
        if res.status_code == 200:
            for item in res.json():
                for char in item.get('usageCharacteristic', []):
                    if char.get('name') == 'EncProductID':
                        offers.append({'desc': item.get('description'), 'enc_id': char.get('value')})
        return offers

def extract_money_amount(flex_data):
    """دالة استخراج المبلغ المحدثة للأمان والدقة"""
    try:
        for item in flex_data:
            if item.get('@type') == 'OTHERS' or item.get('usageType') == 'money':
                for bucket in item.get('bucket', []):
                    if bucket.get('usageType') == 'money':
                        for balance in bucket.get('bucketBalance', []):
                            if balance.get('@type') == 'Remaining':
                                return balance.get('remainingValue', {}).get('amount', 0)
        return 0
    except: return 0

def execute_order(num, token, target_id, flow_type):
    url = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"
    headers = {'Authorization': f'Bearer {token}', 'msisdn': num, 'Content-Type': 'application/json', 'User-Agent': 'okhttp/4.11.0'}
    if flow_type == "REFUND":
        payload = {"orderItem": [{"action": "add", "product": {"characteristic": [{"name": "WorkflowName", "value": "SelfRefund"},{"name": "EncProductID", "value": target_id}],"relatedParty": [{"id": num, "role": "Subscriber"}]}}], "@type": "MoneyBack"}
    else:
        payload = {"orderItem": [{"action": "add", "product": {"characteristic": [{"name": "TariffID", "value": target_id}],"relatedParty": [{"id": num, "role": "Subscriber"}]}}], "@type": "InterventionTariff"}
    res = requests.post(url, json=payload, headers=headers, timeout=30)
    return res.status_code in [200, 201]

def family_op(owner_num, token, member_num, op_type, quota="10", m_token=None):
    url = "https://web.vodafone
