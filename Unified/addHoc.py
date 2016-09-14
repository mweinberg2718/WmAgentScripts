#!/usr/bin/env python  
from utils import workflowInfo, getWorkflows, sendEmail, componentInfo, monitor_dir, reqmgr_url, newLockInfo, siteInfo, sendLog
from assignSession import *
import reqMgrClient
import os
import sys
import json
import time

url = reqmgr_url

## clean out backfills after N days
now = time.mktime(time.gmtime())
def transitiontime(wf, status):
    logs= filter(lambda change : change["Status"]==status, wf['RequestTransition'])
    if logs:
        return logs[-1]['UpdateTime']
    else:
        return None

delays={'assignment-approved' : 7,
        'new':7,
        'completed':14,
        'closed-out':14
        }
for checkin,timeout in delays.items():
    wfs = getWorkflows(url, checkin, user=None, details=True)
    for wf in wfs:
        if not 'backfill' in wf['RequestName'].lower(): continue
        transition = transitiontime(wf,checkin)
        if transition and (now - transition)>(timeout*24*60*60):
            ## that can go away
            print wf['RequestName'],"is old enough to be removed",wf['RequestStatus']
            reqMgrClient.invalidateWorkflow(url, wf['RequestName'], current_status=wf['RequestStatus'])

### dump the knonw thresholds
si = siteInfo()
m = {}
for site in sorted(si.cpu_pledges.keys()):
    print site, si.cpu_pledges[site], int(si.cpu_pledges[site]/2.)
    m[site] = {"running" : si.cpu_pledges[site],
               "pending" : int(si.cpu_pledges[site]/2.)
               }
n = time.gmtime()
m["update"] = time.asctime(n)
m["timestamp"] = time.mktime(n)
open('/afs/cern.ch/user/c/cmst2/www/unified/thresholds.json','w').write(json.dumps( m, indent=2 ))

#nl = newLockInfo()
#nl.lock('/Neutrino_E-10_gun/RunIISpring15PrePremix-AVE_25_BX_25ns_76X_mcRun2_asymptotic_v12-v3/GEN-SIM-DIGI-RAW')
#nl.lock('/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8/RunIISummer15GS-MCRUN2_71_V1_ext1-v2/GEN-SIM')


## all dqmharvest completed to announced right away
wfs = getWorkflows(url, 'completed', user=None, rtype='DQMHarvest')
for wf in wfs: 
    print "closing out",wf
    reqMgrClient.closeOutWorkflow(url, wf)
wfs = getWorkflows(url, 'closed-out', user=None, rtype='DQMHarvest')
for wf in wfs: 
    print "announcing",wf
    reqMgrClient.announceWorkflow(url, wf)
wfs = getWorkflows(url, 'failed', user=None, rtype='DQMHarvest')
if len(wfs):
    sendLog('addHoc','There are failed Harvesting requests\n%s'%('\n'.join(sorted( wfs))),level='critical')

#os.system('Unified/assignor.py')
#os.system('Unified/equalizor.py -a pdmvserv_task_HIG-RunIIFall15DR76-01039__v1_T_160120_002705_9423')
#os.system('Unified/equalizor.py -a pdmvserv_SMP-Summer12DR53X-00027_00440_v0__160224_044437_5031')

up = componentInfo(mcm=False, soft=['mcm'])                                 
if not up.check():  
    sys.exit(1)     


## 
#for wfo in session.query(Workflow).filter(Workflow.status == 'assistance-manual').all():
#    if not any([c in wfo.name for c in ['RunIISpring16DR80']]): continue
#    wfi = workflowInfo(url, wfo.name)
#    if wfi.getRequestNumEvents() < 500000:
#        ## small workflow that needs recovery : kill-clone
#        os.system('Unified/rejector.py --clone %s'%wfo.name)

### catch unrunnable recoveries

"""
### now in GQ.py module
report = ""
not_runable_acdc=set()
wfs = getWorkflows(url, 'acquired', user=None, rtype='Resubmission',details=True)
for wf in wfs:
    wfi = workflowInfo( url , wf['RequestName'], request=wf)
    locs = wfi.getGQLocations()
    wl = set(wfi.request['SiteWhitelist'])
    for wqe,where in locs.items():
        ok = wl & set(where)
        if not ok :
            print "WQE will not run in",wf['RequestName']
            #print list(wl),"does not contain",list(where)
            print "Withlist does not contain",list(where)
            not_runable_acdc.add( wf['RequestName'] )
            report += 'a workqueue element will not run for %s\n'%(wf['RequestName'])
            report += 'whitelist does not contain %s\n'% list(where)
report += '\nfruther check on https://cmst2.web.cern.ch/cmst2/unified/logs/addHoc/last.log\n'

if not_runable_acdc:
    sendEmail('not runnable ACDCs','These %s ACDC cannot run \n%s\n%s'%( len(not_runable_acdc), '\n'.join(not_runable_acdc), report), destination = ['jen_a@fnal.gov','katherine.rozo@cern.ch'])
"""

"""
### add the value of the delay to announcing datasets
data = json.loads(open('%s/announce_delays.json'%monitor_dir).read())
for wfo in session.query(Workflow).filter(Workflow.status.startswith('done')).all()[:500]:
    if wfo.name in data: continue
    wfi = workflowInfo( url, wfo.name)
    closedout_log = filter(lambda change : change["Status"] in ["closed-out"],wfi.request['RequestTransition'])
    announced_log =  filter(lambda change : change["Status"] in ["announced"],wfi.request['RequestTransition'])
    if not closedout_log or not announced_log:
        print "cannot do shit",wfo.name
        continue
    closedout = closedout_log[-1]['UpdateTime']
    announced = announced_log[-1]['UpdateTime'] 
    delay = announced - closedout
    data[wfo.name] = {
        'closedout' : closedout,
        'announced' : announced,
        'delay' : delay
        }
    print wfo.name,"delay",delay
open('%s/announce_delays.json'%monitor_dir,'w').write( json.dumps(data, indent=2) )
"""


#os.system('Unified/assignor.py --go RunIIFall15MiniAODv2 --limit 50')

#print "nothing add-Hoc to be done"
sys.exit(0)


"""
os.system('Unified/equalizor.py -a pdmvserv_SUS-RunIISummer15GS-00049_00173_v0__151222_121539_4448')
os.system('Unified/equalizor.py -a pdmvserv_SUS-RunIISummer15GS-00058_00173_v0__151222_121515_6269')
os.system('Unified/equalizor.py -a pdmvserv_SUS-RunIIWinter15GS-00160_00183_v0__151222_121840_6707')
os.system('Unified/equalizor.py -a  pdmvserv_HIG-RunIISummer15GS-00937_00138_v0__151117_201115_6260')
os.system('Unified/equalizor.py -a  vlimant_HIG-RunIISummer15GS-00935_00138_v0__151223_004144_9025')
os.system('Unified/equalizor.py -a  pdmvserv_HIG-RunIISummer15GS-00073_00169_v0__151217_161512_9524')
os.system('Unified/equalizor.py -a  pdmvserv_EXO-RunIISummer15GS-04765_00148_v0__151204_202120_8377 ')
os.system('Unified/equalizor.py -a  pdmvserv_EXO-RunIISummer15GS-04784_00149_v0__151204_202355_4639 ')
os.system('Unified/equalizor.py -a vlimant_HIG-RunIISummer15GS-01015_00152_v0__151223_191655_2771 ')
os.system('Unified/equalizor.py -a pdmvserv_SUS-RunIISummer15GS-00003_00173_v0__151222_121430_3443')
os.system('Unified/equalizor.py -a pdmvserv_task_TSG-RunIIFall15DR76-00002__v1_T_151118_012230_2147')
os.system('Unified/equalizor.py -a jbadillo_TOP-Summer11LegDR-00039_00062_v0__151216_131228_9019')
"""


#for wfo in session.query(Workflow).filter(Workflow.status == 'staging').all():
#    wfi = workflowInfo(url, wfo.name )
#    if wfi.request['RequestPriority'] < 100000 : continue
#    print "forcing acquiring from staging",wfo.name
#    os.system('Unified/assignor.py --go  %s'% wfo.name)

#for wfo in session.query(Workflow).filter(Workflow.status == 'staged').all():
#    wfi = workflowInfo(url, wfo.name )
#    #if wfi.request['RequestPriority'] < 100000 : continue
#    print "forcing acquiring from staged",wfo.name
#    os.system('Unified/assignor.py --go  %s'% wfo.name)



#for wfo in session.query(Workflow).filter(Workflow.status == 'assistance-manual').all():
#    if 'EXO-RunIIWinter15wmLHE' in wfo.name:
#        print "could reject it but would need the dsn"

#for wfo in session.query(Workflow).filter(Workflow.status == 'assistance-biglumi').all():
#    if 'Summer15' in wfo.name:
#        os.system('Unified/rejector.py --clone %s'% wfo.name)
    
