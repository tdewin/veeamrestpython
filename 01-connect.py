# Very simple example showing just connection to the api
# C:\Users\Administrator\AppData\Local\Programs\Python\Python36\Scripts\pip install requests
import requests

def main():
	server = "127.0.0.1"
	port = 9398
	verifyssl = False
	
	#better in production to have verification and no self signed certificates
	if not verifyssl:
		requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
	
	hrefapi = "https://{server}:{port}/api/".format(server=server,port=port)
	response = requests.get(hrefapi,verify=verifyssl)
	if response.status_code < 400:
		print("Connected Succesfully\n")
		print(response.text)
		
	
if __name__ == "__main__":
    main()