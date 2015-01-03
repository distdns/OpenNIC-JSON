# -*- coding: utf-8 -*-
from __future__ import division
import sys
import os
import dns.query
import dns.zone
import dns.rdatatype
import dns.resolver
import dns.query
import dns.zone
from dns.exception import DNSException
from dns.rdataclass import *
from dns.rdatatype import *
import string
import urllib2
import time
import json
import shelve

nameserver = "188.226.215.149" # OpenNIC nameserver to be used for querying for data

resolver = dns.resolver.Resolver()
resolver.nameservers = [nameserver]
resolver.timeout = 2
resolver.lifetime = 2

try:
	answers = resolver.query(".", 'SOA')
	for data in answers:
		CurrentSOA = string.split(str(data)," ")[2]
		print "Current SOA is "+CurrentSOA
except:
	print "Could not obtain SOA from "+nameserver+ ", exiting."
	quit()


def TestServer(server, uptimeShelve, tlds):
	if(server == "None"):
		return None
	print "Testing Server "+str(server)
	resolver = dns.resolver.Resolver()
	resolver.timeout = 2
	resolver.lifetime = 2
	resolver.nameservers = [server]

	if str(server)+"_up" not in uptimeShelve:
		uptimeShelve[str(server)+"_up"] = 0
		uptimeShelve[str(server)+"_down"] = 0

	try:
		answers = resolver.query(".", 'SOA')
		for data in answers:
				soa = string.split(str(data)," ")[2]

				uptimeShelve[str(server)+"_up"] = uptimeShelve[str(server)+"_up"] + 1
				total = uptimeShelve[str(server)+"_down"] + uptimeShelve[str(server)+"_up"]

				uptime = uptimeShelve[str(server)+"_up"] / total

				soas = []
				for tld in tlds:
					providedSOA = GetSOAforTLD(server, None, tld["tld"])
					if(providedSOA != None and providedSOA >= tld["soa"]):
						current = True
					else:
						current = False
					
					soas.append({
						"tld": tld["tld"],
						"currentSOA": tld["soa"],
						"providedSOA":providedSOA,
						"current": current
					})

				if(soa>=CurrentSOA):
					return {"soa":soa, "current":True, "online": True, "uptime": uptime, "soas": soas}
				else:
					return {"soa":soa, "current":False, "online": True, "uptime": uptime, "soas": soas}
	except Exception as e:
		print e
		uptimeShelve[str(server)+"_down"] = uptimeShelve[str(server)+"_down"] + 1

		if(int(uptimeShelve[str(server)+"_up"]) == 0):
			uptime = float(0)
		else:
			uptime = float(uptimeShelve[str(server)+"_up"]) / (float(uptimeShelve[str(server)+"_down"])+float(uptimeShelve[str(server)+"_up"]))
		
		return {"soa":None, "current":False, "online": False, "uptime": uptime}

def GetSOAforTLD(ns, fallback, tld):
	print "Getting SOA for "+str(tld + " on " + ns)
	resolver = dns.resolver.Resolver()
	resolver.timeout = 2
	resolver.lifetime = 2
	resolver.nameservers = [ns]


	try:
		answers = resolver.query(tld+".", 'SOA')
		for data in answers:
				soa = string.split(str(data)," ")[2]
				return int(soa)
	except:
		try:
			if(fallback != None):
				resolver = dns.resolver.Resolver()
				resolver.nameservers = [fallback]
				resolver.timeout = 2
				resolver.lifetime = 2
				answers = resolver.query(tld+".", 'SOA')
				for data in answers:
						soa = string.split(str(data)," ")[2]
						return int(soa)
			else:
				return None
		except:
			return None;


def GetT2s(n, uptimeShelve, tlds):
	ipv4=True
	ipv6=True
	domain = "dns.opennic.glue"
	answers = dns.resolver.query(domain, 'NS')
	t2s = []

	try:
	        zone = dns.zone.from_xfr(dns.query.xfr(n, domain))
	except DNSException, e:
	        print e.__class__, e


	for name, node in zone.nodes.items():
	        rdatasets = node.rdatasets
	        for rdataset in rdatasets:
	        	if(str(name) != '@'):
	        		loc = str(GetLOCfromNS(n, str(name)))
		        	if(ipv4 and rdataset.rdclass == IN and rdataset.rdtype is A):
						t2s.append({
							"hostname": str(name)+".dns.opennic.glue.",
							"ipv6": None,
							"ipv4": str(rdataset[0]),
							"loc": loc,
							"coords": LOCtoDEC(loc),
							"status": TestServer(str(rdataset[0]), uptimeShelve, tlds)
						})
		        	if(ipv6 and rdataset.rdclass == IN and rdataset.rdtype is AAAA):
						t2s.append({
							"hostname": str(name)+".dns.opennic.glue.",
							"ipv6": str(rdataset[0]),
							"ipv4": None,
							"loc": loc,
							"coords": LOCtoDEC(loc),
							"status": TestServer(str(rdataset[0]), uptimeShelve, tlds)
						})

	return t2s

def GetT1s(n, uptimeShelve, tlds):
	resolver = dns.resolver.Resolver()
	resolver.timeout = 2
	resolver.lifetime = 2
	resolver.nameservers = [n]
	t1s = []
	answers = resolver.query('opennic.glue', 'NS')
	for data in answers:
					ipv4 = None
					ipv6 = None

					try:
						answers = resolver.query(str(data.target), 'AAAA')
						for rdata in answers:
							ipv6 = str(rdata)
					except:
						pass
					
					answers = resolver.query(str(data.target), 'A')
					for rdata in answers:
						ipv4 = str(rdata)

					t1s.append({
						"hostname": str(data.target),
						"ipv6": ipv6,
						"ipv4": ipv4,
						"contact": GetNSContact(n, str(data.target)),
						"status": TestServer(str(ipv4), uptimeShelve, tlds),
						"statusIPv6": TestServer(str(ipv6), uptimeShelve, tlds)
					})

	return t1s

def GetTLDs(n):
	resolver = dns.resolver.Resolver()
	resolver.nameservers = [n]
	resolver.timeout = 2
	resolver.lifetime = 2
	tlds = []
	answers = resolver.query('tlds.opennic.glue', 'TXT')
	for data in answers:
		for tld in data.strings[1:]:
			if(tld == "opennic.glue"):
				tlds.append({
					"tld": tld,
					"operator": "OpenNIC",
					"ns": "ns0",
					"soa": GetSOAforTLD("ns0.opennic.glue", n, tld)
				})
			else:
				ns = GetNSForTLD(n, tld)
				tlds.append({
					"tld": tld,
					"operator": GetTLDContact(n, tld),
					"ns": ns,
					"soa": GetSOAforTLD(str(ns)+".opennic.glue", n, tld)
				})
	return tlds

def GetNewNationsTLDs(n):
	resolver = dns.resolver.Resolver()
	resolver.nameservers = [n]
	resolver.timeout = 2
	resolver.lifetime = 2

	answers = resolver.query('newnations.tlds.opennic.glue', 'TXT')
	for data in answers:
		return data.strings

def GetNSContact(n, ns):
	if "." in ns:
		ns = ns[:-14]

	resolver = dns.resolver.Resolver()
	resolver.nameservers = [n]
	resolver.timeout = 2
	resolver.lifetime = 2

	answers = resolver.query(str(ns)+".opennic.glue.", 'TXT')
	for data in answers:
		if "IRC" in str(data.strings):
			return string.split(string.split(str(data.strings),"'")[1],'=')[1]

def GetNSForTLD(n, tld):
	resolver = dns.resolver.Resolver()
	resolver.nameservers = [n]
	resolver.timeout = 2
	resolver.lifetime = 2

	answers = resolver.query(str(tld)+".opennic.glue.", 'CNAME')
	for data in answers:
		return str(data.target)[:-14]

def GetTLDContact(n, tld):
	ns = GetNSForTLD(n, tld)
	return GetNSContact(n, ns)

def GetLOCfromNS(n, ns):
	resolver = dns.resolver.Resolver()
	resolver.nameservers = [n]
	resolver.timeout = 2
	resolver.lifetime = 2

	try:
		answers = resolver.query(ns+'.dns.opennic.glue', 'LOC')
		for data in answers:
			return data
	except:
		return None

def dms2dec(dms_str):

    dms_str = re.sub(r'\s', '', dms_str)
    
    if re.match('[swSW]', dms_str):
        sign = -1
    else:
        sign = 1
    
    (degree, minute, second, frac_seconds, junk) = re.split('\D+', dms_str, maxsplit=4)

    second += "." + frac_seconds
    return str(sign * (int(degree) + float(minute) / 60 + float(second) / 3600))

def LOCtoDEC(coord):
    if coord == "None":
       	return {
	        "lat": "0",
	        "lng": "0"
	    }

    else:
	    coord = coord.split(' ')

	    if(coord[3] == "S" or coord[3] == "W"):
	        minus1 = "-"
	    else:
	        minus1 = ""

	    if(coord[7] == "S" or coord[7] == "W"):
	        minus2 = "-"
	    else:
	        minus2 = ""

	    firstcoord = coord[0]+"°"+coord[1]+"'"+coord[2]+"\""+coord[3]
	    secondcoord = coord[4]+"°"+coord[5]+"'"+coord[6]+"\""+coord[7]

	    return {
	        "lat": minus1+dms2dec(firstcoord),
	        "lng": minus2+dms2dec(secondcoord)
	    }

if __name__ == "__main__":
	uptimeShelve = shelve.open(sys.path[0] + "/data/uptime.shelve")

	print "\nStarting TLDs"
	tlds = GetTLDs(nameserver)
	data=json.dumps({
		"time": time.time(),
		"expectedSOA": CurrentSOA,
		"data": tlds
	})
	jsonfile=open(sys.path[0] + "/data/tlds.json",'w+')
	jsonfile.write(data)
	jsonfile.close()

	print "\nStarting new-nations TLDs"
	data = json.dumps({
		"time": time.time(),
		"expectedSOA": CurrentSOA,
		"data":GetNewNationsTLDs(nameserver)
	})
	jsonfile=open(sys.path[0] + "/data/newnationstlds.json",'w+')
	jsonfile.write(data)
	jsonfile.close()

	print "\nStarting Tier1s"
	data = json.dumps({
		"time": time.time(),
		"expectedSOA": CurrentSOA,
		"data":GetT1s(nameserver, uptimeShelve, tlds)
	})
	jsonfile=open(sys.path[0] + "/data/tier1s.json",'w+')
	jsonfile.write(data)
	jsonfile.close()

	print "\nStarting Tier2s"
	data = json.dumps({
		"time": time.time(),
		"expectedSOA": CurrentSOA,
		"data":GetT2s(nameserver, uptimeShelve, tlds)
	})
	jsonfile=open(sys.path[0] + "/data/tier2s.json",'w+')
	jsonfile.write(data)
	jsonfile.close()

	uptimeShelve.close()
