# Very simple example showing just connection to the api
# C:\Users\Administrator\AppData\Local\Programs\Python\Python36\Scripts\pip install requests
import requests
import xml.etree.ElementTree as elementtree
import time

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
				
				#find the logout link for later
				hreflogout = None
				hrefjoblist = None
				
				root = elementtree.fromstring(response.text)
				for link in root.iter("{{{ns}}}{tag}".format(ns=xmlnamespace,tag="Link")):
					if "Href" in link.attrib and "Rel" in link.attrib:
						if link.attrib["Rel"] == "Delete":
							hreflogout = link.attrib["Href"]
						elif "Type" in link.attrib and link.attrib["Type"] == "JobReferenceList":
							hrefjoblist = link.attrib["Href"]
				
				try:
					if hrefjoblist:
						#In this case we will look up the jobreferencelist
						#this does not give use the full job detail list but just a very limited representation
						#https://helpcenter.veeam.com/docs/backup/rest/get_jobs.html?ver=95
						#the difference in request is just ?format=entity
						#the response is not the object itself but a reference (tag=Ref) and links to actions
						
						print("Found job refence list link")
						response = requests.get(hrefjoblist,headers=headers,verify=verifyssl)
						if response.status_code < 400:
							root = elementtree.fromstring(response.text)
							
							jobname = "Backup Job 1"
							
							ref = root.find(".//{{{ns}}}{tag}[@Name='{name}']".format(ns=xmlnamespace,tag="Ref",name=jobname))
							if ref:
								print("Job: {0:30} {1}".format(ref.get("Name"),ref.get("UID")))
								entitylinkquery = ref.findall(".//{{{ns}}}{tag}[@Rel='{rel}']".format(ns=xmlnamespace,tag="Link",rel="Alternate"))
								if len(entitylinkquery) > 0:
									joblink = entitylinkquery[0].get("Href")
									print("Found job specific link {0}".format(joblink))
									
									response = requests.get(joblink,headers=headers,verify=verifyssl)
									if response.status_code < 400:
										root = elementtree.fromstring(response.text)
										startlinkquery = root.findall(".//{{{ns}}}{tag}[@Rel='{rel}']".format(ns=xmlnamespace,tag="Link",rel="Start"))
										if len(startlinkquery) > 0:
											startlink = startlinkquery[0].get("Href")
											print("Starting job via {0}".format(startlink))
											
											#start is post -> https://helpcenter.veeam.com/docs/backup/rest/requests.html?ver=95
											response = requests.post(startlink,headers=headers,verify=verifyssl)
											if response.status_code <400:
												print("Request fired succesfully")
												
												root = elementtree.fromstring(response.text)
												state = root.findall(".//{{{ns}}}{tag}".format(ns=xmlnamespace,tag="State"))[0].text
												tasklink = root.findall(".//{{{ns}}}{tag}".format(ns=xmlnamespace,tag="Link"))[0].get("Href")
												
												allowerror = 10
												timeout = 300
												
												while state == "Running" and allowerror > 0 and timeout > 0:
													response = requests.get(tasklink,headers=headers,verify=verifyssl)
													if response.status_code < 400:
														root = elementtree.fromstring(response.text)
														state = root.findall(".//{{{ns}}}{tag}".format(ns=xmlnamespace,tag="State"))[0].text
														print("State : {0}".format(state))
													else:
														allowerror = allowerror - 1
													
													timeout = timeout - 1
													time.sleep(1)
												
												if state == "Finished":
													print("Started succesfully")
												else:
													print("Timeout or too many errors")
												
										else:
											print("Could not find start link")
										
									else:
										print("Error getting job entity ({0})".format(response.status_code)) 
								else:
									print("Cant not find entity link")
							else:
								print("Could not find job {0}".format(jobname))
								
								
						else:
							print("Could not get job list ({0})".format(response.status_code)) 
							
				except Exception as e:
					print("Unexpected error: {0}".format(e))
					
				print("Whatever happens, still trying to logout")
				
				
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