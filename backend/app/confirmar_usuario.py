import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SECRET_KEY")  # precisa ser a service_role key

client = create_client(url, key)

# Troque pelo UID do usuário (coluna "UID" na tela de Users que você mandou)
uid = "75b6560a-7f32-4276-ae9d-66e97f92e02f"  # exemplo: anabeatriz31@gmail.com

resultado = client.auth.admin.update_user_by_id(uid, {"email_confirm": True})
print("Confirmado:", resultado.user.email, resultado.user.email_confirmed_at)