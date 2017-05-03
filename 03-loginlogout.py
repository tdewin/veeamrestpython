# Very simple example showing just connection to the api
# C:\Users\Administrator\AppData\Local\Programs\Python\Python36\Scripts\pip install requests
import requests
import xml.etree.ElementTree as elementtree


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
		hreflogonlink = None
		
		#we need to find the api link so we can authenticate
		#hreflogonlink should be under EnterpriseManager(root)>Links>Link with attibute type eq LogonSession
		#for more info check the login example https://helpcenter.veeam.com/docs/backup/rest/logging_on.html?ver=95
		
		xmlnamespace = "http://www.veeam.com/ent/v1.0"
		rawxml = response.text
		root = elementtree.fromstring(rawxml)
		#iter finds all link elements at any level
		#findall works only at the current level
		for links in root.findall("{{{ns}}}{tag}".format(ns=xmlnamespace,tag="Links")):
			for link in links.iter("{{{ns}}}{tag}".format(ns=xmlnamespace,tag="Link")):
				if "Href" in link.attrib and "Type" in link.attrib and link.attrib["Type"] == "LogonSession":
					hreflogonlink = link.attrib["Href"]
		
		if hreflogonlink != None:
			print("Found logon link: {0}".format(hreflogonlink))
			
			admin = "administrator"
			password = "superduperpassword"
			
			idheader = "X-RestSvcSessionId"
			
			response = requests.post(hreflogonlink,auth=requests.auth.HTTPBasicAuth(admin, password),verify=verifyssl)
			if response.status_code < 400 and idheader in response.headers :
				print("Logged in, got token '{0}'".format(response.headers[idheader]))
				headers = {idheader: response.headers[idheader]}
				
				hreflogout = None
				
				root = elementtree.fromstring(response.text)
				for link in root.iter("{{{ns}}}{tag}".format(ns=xmlnamespace,tag="Link")):
					if "Href" in link.attrib and "Rel" in link.attrib and link.attrib["Rel"] == "Delete":
						hreflogout = link.attrib["Href"]
				
				if hreflogout:
					print("Found logout link: {0}".format(hreflogout))
					response = requests.delete(hreflogout,headers=headers,verify=verifyssl)
					if response.status_code == 204:
						print("Succesfully logged out")
					else:
						print("Could not logout ({0})".format(response.status_code))
					
				else:
					print("Could not find logout link")
			else:
				print("Could not authenticate ({0})".format(response.status_code))
			
		else:
			print("Could not find the api")
		
if __name__ == "__main__":
    main()