import requests

class FileDownloader:
    def download(self, file_url: str) -> str:
        response = requests.get(file_url, stream=True)
        file_path = f"/tmp/{file_url.split('/')[-1]}"
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        return file_path
