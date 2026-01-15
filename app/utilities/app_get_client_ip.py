# Filepath: app/utilities/app_get_client_ip.py
# app/utilities/app_get_client_ip.py

def get_client_ip(request):
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr
