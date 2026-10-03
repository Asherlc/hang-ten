"""Instrumentation only; preserve arithmetic and candidate repair decisions."""
def function(text,name,bucket):
    token='func '+name+'('
    assert text.count(token)==1,token
    offset=text.index('{',text.index(token))+1
    if name=='selfContactPairs':
        assert text[offset:].startswith('\n        contacts(')
        text=text[:offset]+text[offset:].replace('\n        contacts(','\n        return contacts(',1)
    return text[:offset]+f'\n        AcceptedSolverProfile.enter("{bucket}");defer {{AcceptedSolverProfile.leave("{bucket}")}}\n'+text[offset:]

def solver_profile(text,bundle):
    for name,bucket in [('advance','advance'),('correctConstraints','correction'),('contactCorrection','contact'),
                        ('constraintBackbone','backbone'),('merit','merit'),('configurationEvaluation','configuration')]:
        text=function(text,name,bucket)
    needle='        var clearances:[[Double?]]=[]\n'
    assert text.count(needle)==1
    text=text.replace(needle,f'        RopeBundleCensus.build(candidate,epoch:{"bundleEpoch" if bundle else "0"})\n'+needle)
    if bundle:
        needle='state=before;bundleEpoch += 1;cachedEvaluation=nil;lastCorrectionFullStep=false'
        assert text.count(needle)==1
        text=text.replace(needle,'RopeBundleCensus.invalidate("repair");'+needle)
        needle='if bundleHeld.count != count {bundleEpoch += 1;cachedEvaluation=nil}'
        assert text.count(needle)==1
        text=text.replace(needle,'if bundleHeld.count != count {RopeBundleCensus.invalidate("accepted-feature retention");bundleEpoch += 1;cachedEvaluation=nil}')
    return text

def collider_profile(text):
    text=function(text,'fusedChainContacts','wood-original')
    return function(text,'featureChainContacts','wood-bundle')
