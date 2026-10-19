"""A real dated training timetable, distinct from measured progress charts."""
from datetime import date, timedelta
import io

DAY_NAMES = ['Пн','Вт','Ср','Чт','Пт','Сб','Нд']

def calendar_rows(block, today=None, weekdays=None):
    today=today or date.today()
    days=weekdays or block.get('weekdays',[0,2,4])
    if len(days)!=3 or len(set(days))!=3 or any(type(d) is not int or not 0<=d<=6 for d in days):
        raise ValueError('Обери три різні дні тижня.')
    days=sorted(days)
    start=date.fromisoformat(block['schedule_start']) if block.get('schedule_start') else today
    # Begin with the next selected day; never silently add sessions in the past.
    dates=[]; current=start
    while len(dates)<block['length']*3:
        if current.weekday() in days:
            dates.append(current)
        current+=timedelta(days=1)
    return [{'week':i//3+1,'session':i%3,'date':day,'title':block['sessions'][i%3]['title']}
            for i,day in enumerate(dates)]

def timetable(block, completed=None, today=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from exercise_catalog import NAMES
    rows=calendar_rows(block,today)
    # Match actual completed positions in this block, not unrelated diary dates.
    done={x['plan']['cursor']-block['start_cursor'] for x in (completed or [])
          if not x.get('bonus') and block.get('created') and x.get('plan',{}).get('block_id')==block['created']}
    weeks=block['length']
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':10}):
        fig=plt.figure(figsize=(12,2+weeks*.78+3.7),facecolor='#101827')
        ax=fig.add_axes([.06,.37,.88,.49]);ax.axis('off')
        cells=[];colors=[]
        for w in range(weeks):
            group=rows[w*3:w*3+3]
            cells.append([f"Тиждень {w+1}"]+[f"{DAY_NAMES[r['date'].weekday()]} {r['date']:%d.%m}\n{r['title'][:27]}"+(' · виконано' if w*3+i in done else '') for i,r in enumerate(group)])
            colors.append(['#25334b']+[('#215442' if w*3+i in done else '#263956') for i,r in enumerate(group)])
        table=ax.table(cellText=cells,colLabels=['Тиждень','Сесія A','Сесія B','Сесія C'],
                       cellColours=colors,colColours=['#304764']*4,cellLoc='center',loc='center',colWidths=[.16,.28,.28,.28])
        table.auto_set_font_size(False);table.set_fontsize(10)
        for (r,c),cell in table.get_celld().items():
            cell.set_text_props(color='#f1f5ff');cell.set_edgecolor('#101827');cell.set_height(1/(weeks+1))
        status='Затверджений план' if block.get('approved') else 'Проєкт · спочатку підтвердь'
        fig.text(.06,.94,f"Тренування · {weeks} тижнів",color='white',fontsize=23,weight='bold')
        fig.text(.06,.90,status+' · 3 сесії на тиждень',color='#b9cbe4',fontsize=12)
        for i,session in enumerate(block['sessions']):
            lines=[f"{chr(65+i)} · {session['title']}"]
            for item in session['items']:
                lines.append(f"{NAMES[item['exercise']]}\n{item['sets'][0]}–{item['sets'][1]} × {item['reps'][0]}–{item['reps'][1]} · RIR {item['rir'][0]}–{item['rir'][1]}")
            fig.text(.06+i*.30,.32,'\n'.join(lines),va='top',color='#e5edfa',fontsize=9)
        fig.text(.06,.03,'Це розклад, а не прогноз результатів. Робочі кг уточнюються перед сесією за PR, самопочуттям і фактичним RIR.',color='#aebfd8',fontsize=9)
        out=io.BytesIO();fig.savefig(out,format='png',dpi=145,facecolor=fig.get_facecolor());plt.close(fig)
    return out.getvalue()
