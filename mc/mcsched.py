#!/usr/bin/env python -w
import sys,urllib,urllib2,re,time,os
import simplejson as json
import optparse
import httplib
import datetime
import shutil

dashost = 'https://cmsweb.cern.ch'
reqmgrsocket='vocms204.cern.ch'
overview = ''
count = 1

def getzonebyt1(s):
	custodial = '?'
	if not s:
		return custodial
	t1list = {'T1_FR_CCIN2P3':'IN2P3','T1_TW_ASGC':'ASGC','T1_IT_CNAF':'CNAF','T1_US_FNAL':'FNAL','T1_DE_KIT':'KIT','T1_ES_PIC':'PIC','T1_UK_RAL':'RAL'}
	for i in t1list.keys():
		if i in s:
			custodial = t1list[i]
	return custodial

def getWorkflowInfo(workflow):
	conn  =  httplib.HTTPSConnection('cmsweb.cern.ch', cert_file = os.getenv('X509_USER_PROXY'), key_file = os.getenv('X509_USER_PROXY'))
	r1=conn.request('GET','/reqmgr/view/showWorkload?requestName=' + workflow)
	r2=conn.getresponse()
	data = r2.read()
	conn.close()
	list = data.split('\n')

	primaryds = ''
	priority = -1
	timeev = -1
	prepid = ''
	globaltag = ''
	sites = []
	for raw in list:
		if 'primaryDataset' in raw:
			primaryds = raw[raw.find("'")+1:]
			primaryds = primaryds[0:primaryds.find("'")]
		elif 'PrepID' in raw:
			prepid = raw[raw.find("'")+1:]
			prepid = prepid[0:prepid.find("'")]
		elif 'TimePerEvent' in raw:
			a = raw.find("'")
			b = raw.find("'",a+1)
			timeev = int(raw[a+1:b])
		elif 'request.priority' in raw:
			a = raw.find("'")
			if a >= 0:
				b = raw.find("'",a+1)
				priority = int(raw[a+1:b])
			else:
				a = raw.find(" =")
				b = raw.find('<br')
				#print "*%s*" % raw[a+3:b]
				priority = int(raw[a+3:b])
		elif 'white' in raw and not '[]' in raw:
			sites = '['+raw[raw.find("[")+1:raw.find("]")]+']'	
			sites = eval(sites)		
		elif 'request.schema.GlobalTag' in raw:
			globaltag = raw[raw.find("'")+1:]
			globaltag = globaltag[0:globaltag.find(":")]
	custodialt1 = '?'
	for i in sites:
		if 'T1_' in i:
			custodialt1 = i
			break

	conn  =  httplib.HTTPSConnection('cmsweb.cern.ch', cert_file = os.getenv('X509_USER_PROXY'), key_file = os.getenv('X509_USER_PROXY'))
	r1=conn.request('GET','/reqmgr/reqMgr/request?requestName=' + workflow)
	r2=conn.getresponse()
	data = r2.read()
	s = json.loads(data)
	conn.close()
	try:
		filtereff = float(s['FilterEfficiency'])
	except:
		filtereff = -1
	try:
		type = s['RequestType']
	except:
		type = ''
	try:
		status = s['RequestStatus']
	except:
		status = ''
	try:
		reqsize = s['RequestSizeEvents']
	except:
		reqsize = -1
	try:
		inputdataset = s['InputDatasets'][0]
	except:
		inputdataset = ''
	
	if type in ['MonteCarlo']:
		expectedevents = reqsize
	elif type in ['MonteCarloFromGEN']:
		[ie,ist] = getdsdetail(inputdataset)
		expectedevents = int(filtereff*ie)
	else:
		expectedevents = -1
	
	j = {}
	k = {'success':'success','failure':'failure','Pending':'pending','Running':'running','cooloff':'cooloff','pending':'queued','inWMBS':'inWMBS','total_jobs':'total_jobs','local_queue':'local_queue'}
	for r in overview:
		if r['request_name'] == workflow:
			break
	if r:
		for k1 in k.keys():
			k2 = k[k1]
			if k1 in r.keys():
				j[k2] = r[k1]
				j[k2]
			else:
				if k2 == 'local_queue':
					j[k2] = ''
				else:
					j[k2] = 0
	else:
		print " getjobsummary error: No such request: %s" % workflow
		sys.exit(1)
	
	conn  =  httplib.HTTPSConnection('cmsweb.cern.ch', cert_file = os.getenv('X509_USER_PROXY'), key_file = os.getenv('X509_USER_PROXY'))
	r1=conn.request('GET','/reqmgr/reqMgr/outputDatasetsByRequestName?requestName=' + workflow)
	r2=conn.getresponse()
	data = r2.read()
	s = json.loads(data)
	conn.close()
	ods = s
        if len(ods)==0:
                print "No Outpudatasets for this workflow: "+workflow

	duration = timeev*expectedevents/3600
	return {'filtereff':filtereff,'type':type,'status':status,'expectedevents':expectedevents,'inputdataset':inputdataset,'primaryds':primaryds,'prepid':prepid,'globaltag':globaltag,'timeev':timeev,'priority':priority,'sites':sites,'custodialt1':custodialt1,'zone':getzonebyt1(custodialt1),'js':j,'ods':ods,'duration':duration}

def getpriorities(reqinfo):
	priorities = []
	for i in reqinfo.keys():
		if not reqinfo[i]['priority'] in priorities:
			priorities.append(reqinfo[i]['priority'])
	priorities.sort(reverse=True)
	return priorities

def getrequestsByPriority(reqinfo,priority):
	requests = []
	for i in reqinfo.keys():
		if reqinfo[i]['priority'] == priority:
			requests.append(i)
	requests.sort()
	return requests

def getoverview():
	c = 0
	print "Getting overview "
	while c < 3:
		try:
			conn  =  httplib.HTTPSConnection(reqmgrsocket, cert_file = os.getenv('X509_USER_PROXY'), key_file = os.getenv('X509_USER_PROXY'))
			r1=conn.request("GET",'/reqmgr/monitorSvc/requestmonitor')
			r2=conn.getresponse()
			print r2.status, r2.reason
			if r2.status == 500:
				c = c + 1
				print "retrying"
			else:
				c = 100
			s = json.loads(r2.read())
			conn.close()
		except :
			print "Cannot get overview [1]" 
			sys.exit(1)
	if s:
		return s
	else:
		print "Cannot get overview [2]"
		sys.exit(1)

def getRequestsByTypeStatus(typelist,status):
	global overview
	r = []
	for i in overview:
		t = ''
		st = ''
		if 'type' in i.keys():
			t = i['type']
		if 'status' in i.keys():
			st = i['status']
		if t in typelist and st in status:
			r.append(i['request_name'])
	return r
	
def getdsdetail(dataset):
	query = 'dataset dataset=' + dataset + ' status=*|grep dataset.nevents,dataset.status'

	[e,st] = das_get_data(query)
	if e == -1:
		return [0,'']
	else:
		return [e,st]

def das_get_data(query):
    params  = {'input':query, 'idx':0, 'limit':0}
    path    = '/das/cache'
    pat     = re.compile('http[s]{0,1}://')
    if  not pat.match(dashost):
        msg = 'Invalid hostname: %s' % dashost
        raise Exception(msg)
    url = dashost + path
    headers = {"Accept": "application/json"}
    encoded_data = urllib.urlencode(params, doseq=True)
    url += '?%s' % encoded_data
    req  = urllib2.Request(url=url, headers=headers)
    opener = urllib2.build_opener()
    fdesc = opener.open(req)
    data = fdesc.read()
    fdesc.close()

    pat = re.compile(r'^[a-z0-9]{32}')
    if  data and isinstance(data, str) and pat.match(data) and len(data) == 32:
        pid = data
    else:
        pid = None
    count = 1  
    timeout = 30 
    while pid:
        params.update({'pid':data})
        encoded_data = urllib.urlencode(params, doseq=True)
        url  = dashost + path + '?%s' % encoded_data
        req  = urllib2.Request(url=url, headers=headers)
        try:
            fdesc = opener.open(req)
            data = fdesc.read()
            fdesc.close()
        except urllib2.HTTPError:
            print str(urllib2.HTTPError)
            return ""
        if  data and isinstance(data, str) and pat.match(data) and len(data) == 32:
            pid = data
        else:
            pid = None
        time.sleep(1)
    d = eval(data)
    try:
    	r = d['data'][0]['dataset']
    	if isinstance(r,list):
		return [r[0]['nevents'],r[0]['status']]
    	else:
		return [r['nevents'],r['status']]
    except:
	return [-1,'']

def getnextprocessingversion(r):
	c = 0
	[e,st] = [1,'xxx']
	y = 0
	for i in r['ods']:
		if 'GEN-SIM' in i:
			y = 1
			break
	if y:
		while e > 0:
			acqera = getacqera(r)
			c = c + 1
			nextoutputdataset = '/%s/%s-%s-v%s/GEN-SIM' % (r['primaryds'],acqera,r['globaltag'],c)
			#print nextoutputdataset
			[e,st] = getdsdetail(nextoutputdataset)
			#print [e,st]
		return '%s-v%s' % (r['globaltag'],c)
	else:
		return '-'

def getacqera(r):
	prepid = r['prepid']
	return prepid.split('-')[1]

def main():
	global overview,count,jobcount

	overview = getoverview()

	listtype = ['MonteCarlo','MonteCarloFromGEN']
	liststatus = ['assignment-approved']
	list = getRequestsByTypeStatus(listtype,liststatus)

	#list = list[1:10]
	list.sort()
	reqinfo = {}

	if os.path.exists('reqinfo.txt'):
		reqinfo = open('reqinfo.txt').read()
		reqinfo = eval(reqinfo)
	else:
		for workflow in list:
			sys.stdout.write("\rAnalyzing requests in %s: %s/%s" % (liststatus,count,len(list))) 
			sys.stdout.flush()
	
			reqinfo[workflow] = getWorkflowInfo(workflow)

			count = count + 1
	print
	output = open('reqinfo.txt', 'w')
	output.write("%s" % reqinfo)
	output.close()

	priorities = getpriorities(reqinfo)
	print 'REQUEST PRIORITY EVENTS DURATION ACQERA PROCESSINGVERSION'
	for p in range(0,len(priorities)):
		for i in getrequestsByPriority(reqinfo,priorities[p]):
			acqera = getacqera(reqinfo[i])
			procversion = getnextprocessingversion(reqinfo[i])
			print "%s %s %s %s %s %s" %(i,reqinfo[i]['priority'],reqinfo[i]['expectedevents'],reqinfo[i]['duration'],acqera,procversion)

        sys.exit(0)

if __name__ == "__main__":
        main()
