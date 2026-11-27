from pathlib import Path
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib.auth import logout

OUT = 'https://erp.example.com/login?logged_out=1'
SCRIPT = Path(__file__).with_name('session.js').read_bytes()
class WorkspaceSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        if request.path == '/cloud-session.js':
            response = HttpResponse(SCRIPT, content_type='application/javascript')
            response['Cache-Control'] = 'no-store'
            return response
        if request.user.is_authenticated:
            epoch = request.COOKIES.get('cloud_logout_epoch', '')
            previous = request.session.get('cloud_browser_epoch')
            if previous is None:
                request.session['cloud_browser_epoch'] = epoch
            elif previous != epoch:
                logout(request)
                if request.path.startswith('/api/'):
                    return JsonResponse({'detail': 'Signed out of workspace'}, status=401)
                return HttpResponseRedirect(OUT)
        response = self.get_response(request)
        if request.user.is_authenticated and not response.streaming and 'text/html' in response.get('Content-Type', '') and not response.get('Content-Encoding'):
            content = response.content
            if b'</body>' in content:
                response.content = content.replace(b'</body>', b'<script src="/cloud-session.js?v=20261127-desk" defer></script></body>')
                response['Content-Length'] = str(len(response.content))
        return response
