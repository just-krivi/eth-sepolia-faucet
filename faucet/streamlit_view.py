import subprocess
from django.views.generic import TemplateView
from django.http import HttpResponse, StreamingHttpResponse
import requests
from urllib.parse import urljoin
import time

class StreamlitProxyView(TemplateView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.streamlit_process = None
        self.streamlit_url = "http://localhost:8501"

    def start_streamlit(self):
        if self.streamlit_process is None:
            self.streamlit_process = subprocess.Popen(
                [
                    "streamlit", "run", 
                    "faucet/streamlit_app.py", 
                    "--server.port", "8501",
                    "--server.address", "0.0.0.0",
                    "--browser.serverAddress", "localhost",
                    "--server.baseUrlPath", "",
                    "--server.enableCORS", "false",
                    "--server.enableXsrfProtection", "false",
                    "--theme.base", "light",
                ]
            )
            time.sleep(3)

    def proxy_request(self, request, path):
        """Proxy a request to Streamlit"""
        # Handle special paths
        if path.startswith('/static/'):
            streamlit_path = f'_stcore/static/{path.replace("/static/", "", 1)}'
        else:
            streamlit_path = path.lstrip('/')

        # Construct the full Streamlit URL
        url = urljoin(self.streamlit_url, streamlit_path)
        
        try:
            # Forward the request to Streamlit
            streamlit_response = requests.get(
                url,
                stream=True,
                headers={
                    'Accept': request.headers.get('Accept', ''),
                    'Accept-Encoding': request.headers.get('Accept-Encoding', ''),
                    'User-Agent': request.headers.get('User-Agent', ''),
                }
            )
            
            # Get content type, defaulting to text/html
            content_type = streamlit_response.headers.get('Content-Type', 'text/html')
            
            # Create the response
            if 'stream' in content_type:
                response = StreamingHttpResponse(
                    streamlit_response.iter_content(chunk_size=8192),
                    content_type=content_type
                )
            else:
                response = HttpResponse(
                    streamlit_response.content,
                    content_type=content_type
                )
            
            # Copy all headers from Streamlit response
            excluded_headers = [
                'content-encoding', 
                'content-length', 
                'transfer-encoding', 
                'connection'
            ]
            for header, value in streamlit_response.headers.items():
                if header.lower() not in excluded_headers:
                    response[header] = value
            
            return response
            
        except requests.RequestException as e:
            return HttpResponse(f"Error: {str(e)}", status=500)

    def get(self, request, *args, **kwargs):
        try:
            # Get the path including query parameters
            path = request.get_full_path()
            
            # Try to proxy the request
            return self.proxy_request(request, path)
            
        except requests.RequestException:
            # If Streamlit isn't running, start it
            self.start_streamlit()
            return HttpResponse(
                """
                <html>
                    <head>
                        <title>Loading Streamlit...</title>
                        <meta http-equiv='refresh' content='3'>
                        <style>
                            body { 
                                font-family: Arial, sans-serif; 
                                text-align: center; 
                                padding-top: 50px;
                                background-color: #f5f5f5;
                            }
                            .loader {
                                border: 4px solid #f3f3f3;
                                border-radius: 50%;
                                border-top: 4px solid #3498db;
                                width: 40px;
                                height: 40px;
                                animation: spin 1s linear infinite;
                                margin: 20px auto;
                            }
                            @keyframes spin {
                                0% { transform: rotate(0deg); }
                                100% { transform: rotate(360deg); }
                            }
                        </style>
                    </head>
                    <body>
                        <h2>Starting Streamlit application...</h2>
                        <div class="loader"></div>
                        <p>Please wait, this may take a few seconds.</p>
                    </body>
                </html>
                """
            ) 