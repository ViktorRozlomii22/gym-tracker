"""Opt-in evaluation against a real local model using synthetic athletes only."""
import copy
from datetime import datetime
import json
import time
from pathlib import Path
import coach_rag as rag
from paths import DATA_DIR

def athlete(now):
    return {'profile':{'вік':30,'зріст':180,'вага':80,'досвід':4,'крок':2.5,'мета':'м’язи','обладнання':'зал'},
        'prs':{k:{'weight':w,'reps':5,'date':now.date().isoformat(),'e1rm':w*(1+5/30)}
               for k,w in [('squat',100),('bench',80),('deadlift',120),('row',60),('press',45)]},
        'program':'fullbody','cursor':0,'health':'ready','return_left':0,'completed':[],
        'events':[],'feedback':{},'pending':None,'block':None,'exercise_feedback':[],'checkin':None}

def run_suite(destination=None, selected=None):
    from ai_setup import available_models
    models=available_models()
    if models is None or not any(m==rag.model_name() or m==rag.model_name()+':latest' for m in models):
        raise RuntimeError('Real-model evaluation unavailable. Start Ollama and install '+rag.model_name()+
            ' using SETUP_AI.cmd, then run EVALUATE_AI.cmd. No mocked result is reported as a real pass.')
    from training_cycle import propose_block, swap_proposal
    now=datetime.now(); base=athlete(now)
    cases=[]
    def record(name, action):
        if selected is not None and name not in selected:
            return
        print('Evaluating: '+name,flush=True)
        started=time.monotonic()
        try:
            output=action()
            cases.append({'case':name,'status':'accepted_by_app_guards','seconds':round(time.monotonic()-started,2),'output':output})
        except (ValueError,RuntimeError) as error:
            cases.append({'case':name,'status':'rejected_or_failed','seconds':round(time.monotonic()-started,2),'error':str(error)})
        print('  '+cases[-1]['status']+(' - '+cases[-1]['error'] if 'error' in cases[-1] else ''),flush=True)
        folder=Path(destination) if destination else DATA_DIR/'evaluation'
        folder.mkdir(parents=True,exist_ok=True)
        progress={'created':now.isoformat(),'model':rag.model_name(),'mocked':False,'cases':cases,'incomplete':True}
        (folder/'evaluation-in-progress.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2),encoding='utf-8')
    record('experienced_session',lambda:rag.generate(copy.deepcopy(base),now,False,False))
    no_pr=copy.deepcopy(base); no_pr['prs']={}
    def missing_reference():
        result=rag.generate(no_pr,now,False,False)
        if any(x['weight'] is not None for x in result['items']):
            raise ValueError('Invented weight without a strength reference.')
        return result
    record('no_strength_reference',missing_reference)
    recovered=copy.deepcopy(base); recovered['return_left']=3
    record('recovery_session',lambda:rag.generate(recovered,now,False,True))
    def block_workflow():
        state=copy.deepcopy(base)
        block=propose_block(state,4,now)
        intermediate=Path(destination) if destination else DATA_DIR/'evaluation'
        intermediate.mkdir(parents=True,exist_ok=True)
        (intermediate/'last-generated-block.json').write_text(json.dumps(block,ensure_ascii=False,indent=2),encoding='utf-8')
        block.update(approved=True,start_cursor=0); state['block']=block
        first=rag.generate(state,now,False,False)
        return {'block':block,'first_session':first}
    record('four_week_block',block_workflow)
    swap=copy.deepcopy(base)
    source=next(c for c in rag.library()['cards'] if c['id']=='acsm2026')
    swap['pending']={'day':now.date().isoformat(),'program':'fullbody','cursor':0,'bonus':False,'recovery':False,
        'approved':True,'items':[{'key':'bench','sets':2,'reps':8,'rir':3,'weight':50,'basis':'Синтетичний тест.',
        'citations':['acsm2026']}],'sources':[source],'rationale':'Синтетичний тест.','uncertainty':'Тест.'}
    record('equipment_swap_without_variant_pr',lambda:swap_proposal(swap,'bench','лавка зайнята',now))
    record('evidence_question',lambda:rag.answer('Чому не кожен підхід до відмови? RIR hypertrophy',base,now))
    report={'created':now.isoformat(),'model':rag.model_name(),'knowledge_sha256':rag.library()['sha256'],
        'synthetic_data_only':True,'mocked':False,'cases':cases,
        'accepted':sum(x['status']=='accepted_by_app_guards' for x in cases),'total':len(cases),
        'interpretation':'App guards check structure, references and conservative load limits. Acceptance does not prove scientific accuracy, Ukrainian fluency, citation entailment or suitability for a person. Review every output manually.',
        'manual_review_required':True}
    folder=Path(destination) if destination else DATA_DIR/'evaluation'
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/f'qwen-{now.strftime("%Y%m%d-%H%M%S")}.json'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (folder/'evaluation-in-progress.json').unlink(missing_ok=True)
    return path,report

def main():
    print('REAL LOCAL AI EVALUATION\nSynthetic data only. Six cases; this can take several minutes on a CPU.')
    path,report=run_suite()
    print(f'{report["accepted"]}/{report["total"]} responses accepted by app guards. Report: {path}')
    print('Read the report and review the outputs. Guard acceptance is not a scientific quality certificate.')

if __name__=='__main__':
    main()
