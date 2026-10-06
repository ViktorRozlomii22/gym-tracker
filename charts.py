from datetime import date, timedelta

def chart(rows, days, target=None, today=None):
    import io
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    training = [r for r in rows if r['kind'] == 'training']
    measures = [r for r in rows if r['kind'] == 'measurement']
    if target and training:
        specs = [('Найбільша записана вага', 'кг', 'max'), ('Усього повторень', 'повт.', 'reps'), ('Обсяг тренування', 'кг × повт.', 'volume')]
    elif target and measures:
        specs = [(target.title(), measures[0]['unit'], 'measure')]
    else:
        specs = [('Обсяг тренування за день', 'кг × повт.', 'volume'), ('Підходи за день', 'Підходи', 'sets')]
    with plt.rc_context({'figure.facecolor': '#101827', 'axes.facecolor': '#101827', 'text.color': '#edf3fc', 'axes.labelcolor': '#c1cede', 'xtick.color': '#c1cede', 'ytick.color': '#c1cede', 'axes.edgecolor': '#364357', 'font.size': 10}):
        fig, axes = plt.subplots(len(specs), 1, figsize=(10, 3.1 * len(specs)), squeeze=False, layout='constrained')
        fig.suptitle(f'{target.title() if target else "Твої тренування"} · останні {days} днів', fontsize=18, fontweight='bold')
        for ax, (title, unit, metric) in zip(axes[:, 0], specs):
            grouped = {}
            for row in measures if metric == 'measure' else training:
                d = date.fromisoformat(row['day'])
                if metric in ('measure', 'max'):
                    grouped[d] = row['value'] if metric == 'measure' else max(grouped.get(d, 0), row['value'])
                else:
                    v = row['sets'] * row['reps'] * row['value'] if metric == 'volume' else row['sets'] * row['reps'] if metric == 'reps' else row['sets']
                    grouped[d] = grouped.get(d, 0) + v
            x = sorted(grouped)
            y = [grouped[d] for d in x]
            if metric in ('measure', 'max'):
                ax.plot(x, y, '-o', color='#66e2bb', linewidth=2.5, markersize=6)
            else:
                ax.bar(x, y, color='#66e2bb', width=max(0.6, days / 150))
                ax.set_ylim(bottom=0)
            ax.set(title=title, ylabel=unit, xlim=(start - timedelta(days=1), today + timedelta(days=1)))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=8))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%y'))
            ax.grid(axis='y', alpha=0.15)
            ax.set_axisbelow(True)
            if not x:
                ax.text(0.5, 0.5, 'Немає записів про тренування', transform=ax.transAxes, ha='center')
        output = io.BytesIO()
        fig.savefig(output, format='png', dpi=130)
        plt.close(fig)
        return output.getvalue()
