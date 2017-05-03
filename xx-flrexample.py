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
				hrefqueryservice = None
				hreflookupservice = None 
				
				root = elementtree.fromstring(response.text)
				for link in root.iter("{{{ns}}}{tag}".format(ns=xmlnamespace,tag="Link")):
					if "Href" in link.attrib and "Rel" in link.attrib:
						if link.attrib["Rel"] == "Delete":
							hreflogout = link.attrib["Href"]
						elif "Type" in link.attrib:
							if link.attrib["Type"] == "QueryService":
								hrefqueryservice = link.attrib["Href"]
							elif link.attrib["Type"] == "LookupService": 
								hreflookupservice = link.attrib["Href"]
				
				try:
					if hrefqueryservice and hreflookupservice:
						querylink = hrefqueryservice.replace("querySvc","query")
						lookuplink = hreflookupservice.replace("lookupSvc","lookup")
						
						hostname = "esx01.local"
						vmname = "adalone"
						
						platformid = None
						
						params={'type':'HierarchyRoot','format':'entities','filter':'Name=="{0}"'.format(hostname)}
						response = requests.get(querylink,headers=headers,verify=verifyssl,params=params)
						if response.status_code < 400:
							root = elementtree.fromstring(response.text)
							mss = root.findall(".//{{{0}}}HierarchyRoot".format(xmlnamespace))
							if len(mss) > 0:
								platformid = mss[0].get("UID")
							
								params={'host':platformid,'type':'VM','name':vmname}
								response = requests.get(lookuplink,headers=headers,verify=verifyssl,params=params)
								if response.status_code < 400:
									root = elementtree.fromstring(response.text)
									objectquery = root.findall(".//{{{0}}}ObjectRef".format(xmlnamespace))
									if len(objectquery) > 0:
										object = objectquery[0].text
										
										#sort by name desc will bring the newest one on top
										params={'type':'VmRestorePoint','format':'entities','filter':'HierarchyObjRef=="{0}"'.format(object),'sortDesc':'Name'}
										response = requests.get(querylink,headers=headers,verify=verifyssl,params=params)
										
										if response.status_code < 400:
											root = elementtree.fromstring(response.text)
											
											
											restorepoints =  root.findall(".//{{{0}}}VmRestorePoint".format(xmlnamespace))
											if len(restorepoints) > 0:
												restorepoint = restorepoints[0]
												
												namedate = restorepoint.get("Name").split("@")
												if len(namedate) > 1:
													name = "@".join(namedate[0:len(namedate)-1])
													date = namedate[len(namedate)-1]
													
													href = restorepoint.get("Href")

													print("{0} {1} {2}".format(name,date,href))
													
													response = requests.get(href,headers=headers,verify=verifyssl)
													if response.status_code < 400:
														root = elementtree.fromstring(response.text)
														mountquery = root.findall(".//{{{0}}}Link[@Rel='Create']".format(xmlnamespace))
														if len(mountquery) > 0:
															mountlink = mountquery[0].get('Href')
															response = requests.post(mountlink,headers=headers,verify=verifyssl)
															if response.status_code < 400:
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
																	root = elementtree.fromstring(response.text)
																	mountquery = root.findall(".//{{{ns}}}Link[@Type='VmRestorePointMount']".format(ns=xmlnamespace))
																	if len(mountquery) > 0:
																		mountpointlink = mountquery[0].get("Href")
																		response = requests.get(mountpointlink,headers=headers,verify=verifyssl)
																		if response.status_code < 400:
																			try:
																				filename = "c:\\data\\fnames.txt".replace("\\","/")
																				response  = requests.get("{0}/{1}".format(mountpointlink,filename),headers=headers,verify=verifyssl)
																				if response.status_code < 400:
																					root = elementtree.fromstring(response.text)
																					restorequery = root.findall(".//{{{ns}}}Link[@Rel='Restore']".format(ns=xmlnamespace))
																					if len(restorequery) > 0:
																						restorelink = restorequery[0].get("Href")
																						fordownloadxml = '<?xml version="1.0" encoding="utf-8"?><FileRestoreSpec xmlns="http://www.veeam.com/ent/v1.0" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><ForDirectDownload/></FileRestoreSpec>'
																						
																						headersxmlpost = {'Content-Type': 'application/xml',idheader:headers[idheader]}
																						response = requests.post(restorelink,headers=headersxmlpost,verify=verifyssl,data=fordownloadxml)
																						if response.status_code < 400:
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
																								root = elementtree.fromstring(response.text)
																								downloadquery = root.findall(".//{{{ns}}}Link[@Rel='Download']".format(ns=xmlnamespace))
																								if len(downloadquery) > 0:
																									response = requests.get(downloadquery[0].get("Href"),headers=headers,verify=verifyssl)
																									if response.status_code < 400:
																										print(response.text)
																									else:
																										print("Could not download file")
																								
																						else:
																							print("Could not start restoreprocess ({0})".format(response.status_code))
																							print(response.text)
																				else:
																					print("Could not get file : {0}".format(filename))
																			except Exception as e:
																				print("Unexpected error in file browsing: {0}".format(e))
																		
																		print("Trying to unmount in all cases")
																		
																		response = requests.delete(mountpointlink,headers=headers,verify=verifyssl)
																		if response.status_code == 204:
																			print("Deleted mount point succesfully")
																		else:
																			print("Could not delete mountpoint ({0})".format(response.status_code))
																		
																else:
																	print("Unable to mount")															
														else:
															print("Could not find mount link")
													else:
														print("Could not get restorepoint details ({0})".format(response.status_code))
												else:
													print("Unsuccesful splitting {0}".format(namedate))
											else:
												print("Could not find a restorepoint in response")
										else:
											print("Could not get restorepoint ({0})".format(response.status_code))
									else:
										print("Could not get vm from xml")
								else:
									print("Could not get vm ({0})".format(response.status_code))
									print(response.text)
								
							
						else:
							print("Could not get root ({0})".format(response.status_code))
							print(response.text)					
								
								
								
						
					else:
						print("Did not find catalog link")
							
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