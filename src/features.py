"""Training-only transparent encoding; source IDs and outcomes never features."""
import numpy as np
from scipy.spatial.distance import cdist

NUMERIC=['log_stress','load_ratio','direction','power','scan_speed','hatch_space',
    'layer_thickness','heat_temperature','heat_time']
CATEGORICAL=['surface','thermal']

class Encoder:
    def __init__(self,mode='rich'): self.mode=mode
    def fit(self,df):
        self.numeric=NUMERIC if self.mode=='rich' else ['log_stress','load_ratio']
        self.categorical=CATEGORICAL if self.mode=='rich' else []
        a=df[self.numeric].to_numpy(float)
        self.med=np.array([np.nanmedian(c) if np.isfinite(c).any() else 0 for c in a.T])
        a=np.where(np.isfinite(a),a,self.med)
        self.mean=a.mean(axis=0);self.sd=a.std(axis=0);self.sd[self.sd<1e-8]=1.
        self.categories={c:sorted(set(df[c].fillna('unknown').astype(str)))+['__unseen__'] for c in self.categorical}
        self.names=self.numeric+[f'{x}_missing' for x in self.numeric]+[f'{c}={v}' for c in self.categorical for v in self.categories[c]]
        return self
    def transform(self,df):
        a=df[self.numeric].to_numpy(float);missing=~np.isfinite(a)
        num=(np.where(missing,self.med,a)-self.mean)/self.sd
        arrays=[num,missing.astype(float)]
        for c in self.categorical:
            cat=self.categories[c];vals=df[c].fillna('unknown').astype(str).to_numpy()
            vals=np.where(np.isin(vals,cat),vals,'__unseen__')
            arrays.append(np.column_stack([vals==x for x in cat]).astype(float))
        return np.column_stack(arrays)
    def receipt(self): return {'mode':self.mode,'numeric':self.numeric,'median':self.med.tolist(),'mean':self.mean.tolist(),'sd':self.sd.tolist(),'categories':self.categories,'names':self.names}

def support_distance(train_x,query_x):
    return np.sqrt(cdist(query_x,train_x,'sqeuclidean').min(axis=1)/train_x.shape[1])

