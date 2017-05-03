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
		print(root.tag)
		#iter finds all link elements at any level
		#findall works only at the current level
		for links in root.findall("{{{ns}}}{tag}".format(ns=xmlnamespace,tag="Links")):
			print(links.tag)
			for link in links.iter("{{{ns}}}{tag}".format(ns=xmlnamespace,tag="Link")):
				if "Href" in link.attrib and "Type" in link.attrib and link.attrib["Type"] == "LogonSession":
					print(" {tag:30}\n  {rel:10} {type:15} {href}".format(tag=link.tag,rel=link.attrib["Rel"],type=link.attrib["Type"],href=link.attrib["Href"]))
					hreflogonlink = link.attrib["Href"]
		
		print("\n")
		if hreflogonlink != None:
			print("Found logon link: {0}".format(hreflogonlink))
		else:
			print("Could not find the api")
		
if __name__ == "__main__":
    main()