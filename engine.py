import requests
import json
import asyncio
import aiohttp
import random

# --- الإعدادات والقوائم الأساسية ---

# باقات فليكس ديسكونت المرتبة
PACKAGES = {
    "8": {"tariff_id": "511", "product_id": "Flex_2021_511", "price": "20.0", "desc": "فليكس 40"},
    "10": {"tariff_id": "627", "product_id": "Flex_2024_627", "price": "25.0", "desc": "فليكس 45"},
    "7": {"tariff_id": "513", "product_id": "Flex_2021_513", "price": "30.0", "desc": "فليكس 60"},
    "6": {"tariff_id": "629", "product_id": "Flex_2024_629", "price": "35.0", "desc": "فليكس 70"},
    "5": {"tariff_id": "515", "product_id": "Flex_2021_515", "price": "45.0", "desc": "فليكس 90"},
    "4": {"tariff_id": "631", "product_id": "Flex_2024_631", "price": "50.0", "desc": "فليكس 100"},
    "3": {"tariff_id": "517", "product_id": "Flex_2021_517", "price": "65.0", "desc": "فليكس 130"},
    "2": {"tariff_id": "633", "product_id": "Flex_2024_633", "price": "75.0", "desc": "فليكس 150"},
    "1": {"tariff_id": "523", "product_id": "Flex_2021_523", "price": "130.0", "desc": "فليكس 260"},
    "9": {"tariff_id": "637", "product_id": "Flex_2024_637", "price": "150.0", "desc": "فليكس 300"}
}

USER_AGENTS_APPLE = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
]

# --- وظائف المصادقة والتوكن ---

def get_token(num, pwd):
    """جلب التوكن باستخدام هيدرز الفحص (Synchronous)"""
    url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
    payload = {
        'username': num, 'password': pwd, 'grant_type': 'password',
        'client_secret': 'a2ec6fff-0b7f-4aa4-a733-96ceae5c84c3', 'client_id': 'my-vodafone-app'
    }
    headers = {
        'User-Agent': 'okhttp/4.9.3', 'x-agent-operatingsystem': 'V12.5.13.0.RJQMIXM',
        'clientId': 'xxx', 'x-agent-device': 'lime', 'x-agent-version': '2024.10.1', 'x-agent-build': '562'
    }
    res = requests.post(url, data=payload, headers=headers, timeout=20)
    if res.status_code == 200: return res.json().get('access_token')
    raise Exception("فشل تسجيل الدخول: تأكد من الرقم وكلمة المرور")

async def get_token_async(session, num, pwd):
    """جلب التوكن بشكل غير متزامن للعمليات السريعة"""
    url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
    data = {
        'grant_type': 'password', 'username': num, 'password': pwd,
        'client_id': 'ana-vodafone-app', 'client_secret': '95fd95fb-7489-4958-8ae6-d31a525cd20a'
    }
    async with session.post(url, data=data) as res:
        if res.status == 200:
            json_data = await res.json()
            return json_data.get('access_token')
    return None

# --- وظائف الماني باك (Oppo Headers) ---

def run_money_back_scan(num, token):
    """فحص رصيد الماني باك المتاح"""
    headers = {
        'channel': 'MOBILE', 'useCase': 'Promo', 'Authorization': f'Bearer {token}',
        'api-version': 'v2', 'x-agent-operatingsystem': '11', 'clientId': 'AnaVodafoneAndroid',
        'x-agent-device': 'OPPO CPH2059', 'x-agent-version': '2024.3.3', 'x-agent-build': '593',
        'msisdn': num, 'Content-Type': 'application/json', 'Accept': 'application/json'
    }
    url = f'https://web.vodafone.com.eg/services/dxl/usage/usageConsumptionReport?bucket.product.publicIdentifier={num}&@type=aggregated'
    res = requests.get(url, headers=headers, timeout=20)
    if res.status_code == 200:
        for item in res.json():
            if item.get('@type') == 'OTHERS':
                for b in item.get('bucket', []):
                    if b.get('usageType') == 'money':
                        for bal in b.get('bucketBalance', []):
                            if bal.get('@type') == 'Remaining':
                                return bal.get('remainingValue', {}).get('amount', 0)
    return 0

# --- وظائف فليكس ديسكونت (Xiaomi Payload) ---

def execute_flex_discount(num, token, pkg_key):
    """تفعيل خصم باقة فليكس"""
    pkg = PACKAGES[pkg_key]
    url = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"
    headers = {
        'User-Agent': "okhttp/4.11.0", 'Authorization': f"Bearer {token}",
        'msisdn': num, 'Content-Type': "application/json; charset=UTF-8"
    }
    payload = {
        "channel": {"name": "MobileApp"},
        "orderItem": [{
            "action": "add", "id": pkg['product_id'],
            "itemPrice": [{"name": "OriginalPrice", "price": {"taxIncludedAmount": {"unit": "LE", "value": pkg['price']}}}, {"name": "MigrationFees", "price": {"taxIncludedAmount": {"unit": "LE", "value": "0.0"}}}],
            "product": {
                "characteristic": [{"name": "offerRank", "value": "1"}, {"name": "TariffID", "value": pkg['tariff_id']}, {"name": "Validity", "@type": "MONTH", "value": "1"}, {"name": "TariffRank", "value": "6"}],
                "productSpecification": [{"id": "Retention With Offer", "name": "Category"}, {"id": "Flex Family", "name": "BundleType"}],
                "relatedParty": [{"id": num, "role": "Subscriber"}]
            },
            "@type": "Access fees Discount"
        }],
        "@type": "InterventionTariff"
    }
    res = requests.post(url, json=payload, headers=headers, timeout=20)
    try: return res.json().get('reason') == "Success With Grace"
    except: return False

# --- وظائف التطيير المتزامن (Async System) ---

async def add_member_async(session, token, owner, member, quota):
    """إرسال طلب إضافة فرد (غير متزامن)"""
    url = "https://web.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
    payload = {
        "name": "FlexFamily", "type": "SendInvitation",
        "category": [
            {"value": "523", "listHierarchyId": "PackageID"},
            {"value": "47", "listHierarchyId": "TemplateID"},
            {"value": "percentage", "listHierarchyId": "familybehavior"}
        ],
        "parts": {
            "member": [
                {"id": [{"value": owner, "schemeName": "MSISDN"}], "type": "Owner"},
                {"id": [{"value": member, "schemeName": "MSISDN"}], "type": "Member"}
            ],
            "characteristicsValue": {
                "characteristicsValue": [{"characteristicName": "quotaDist1", "value": str(quota), "type": "percentage"}]
            }
        }
    }
    headers = {
        'Authorization': f"Bearer {token}", 'msisdn': owner,
        'Content-Type': "application/json", 'User-Agent': random.choice(USER_AGENTS_APPLE),
        'clientId': "WebsiteConsumer"
    }
    try:
        async with session.post(url, json=payload, timeout=15) as res:
            return res.status in [200, 201, 204]
    except: return False

async def remove_member_async(session, token, owner, member):
    """تنظيف العملية (حذف العضو) في حال فشل التطيير"""
    url = "https://web.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
    payload = {
        "name": "FlexFamily", "type": "FamilyRemoveMember",
        "category": [{"value": "47", "listHierarchyId": "TemplateID"}],
        "parts": {
            "member": [
                {"id": [{"value": owner, "schemeName": "MSISDN"}], "type": "Owner"},
                {"id": [{"value": member, "schemeName": "MSISDN"}], "type": "Member"}
            ],
            "characteristicsValue": {
                "characteristicsValue": [{"characteristicName": "Disconnect", "value": "0"}, {"characteristicName": "LastMemberDeletion", "value": "1"}]
            }
        }
    }
    headers = {'Authorization': f"Bearer {token}", 'msisdn': owner, 'Content-Type': "application/json"}
    try:
        async with session.patch(url, json=payload, timeout=15) as res:
            return res.status in [200, 201, 204]
    except: return False

async def accept_invitation_async(session, owner, member, m_token):
    """قبول الدعوة باستخدام توكن العضو"""
    url = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
    data = {
        "category": [{"listHierarchyId": "TemplateID", "value": "47"}],
        "name": "FlexFamily",
        "parts": {
            "member": [
                {"id": [{"schemeName": "MSISDN", "value": owner}], "type": "Owner"},
                {"id": [{"schemeName": "MSISDN", "value": member}], "type": "Member"}
            ]
        },
        "type": "AcceptInvitation"
    }
    headers = {
        "Authorization": f"Bearer {m_token}", "msisdn": member,
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "VodafoneEG/5.5.1 (iPhone; iOS 16.6)",
        "clientId": "AnaVodafoneAndroid"
    }
    try:
        async with session.patch(url, json=data, timeout=15) as res:
            return res.status in [200, 201]
    except: return False
