import firebase_admin
from firebase_admin import credentials, auth
import sys

if not firebase_admin._apps:
    cred = credentials.Certificate('data/firebase-service-account.json')
    firebase_admin.initialize_app(cred)

uid = 'R2DWb3KnUMcjVCN78lKrtNAw8PA3'
auth.set_custom_user_claims(uid, {'role': 'ADMIN'})
user = auth.get_user(uid)
print(f'User: {user.email}')
print(f'Custom claims: {user.custom_claims}')
print('Role set to ADMIN successfully!')
