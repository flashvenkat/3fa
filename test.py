import urllib.request, json
data = json.dumps({'username':'test_500', 'password':'p', 'face_image':'data:image/jpeg;base64,/9j/4AAQSkZJRg==', 'email':'a', 'full_name':'b', 'dob':'c', 'phone':'d', 'state':'e', 'country':'f'}).encode('utf-8')
req = urllib.request.Request('http://127.0.0.1:5000/register', data=data, headers={'Content-Type': 'application/json'})
try:
    resp = urllib.request.urlopen(req)
    print("STATUS:", resp.getcode())
    print("BODY:", resp.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print("ERROR STATUS:", e.code)
    print("ERROR BODY:", e.read().decode('utf-8'))
except Exception as e:
    print("OTHER ERROR:", e)
