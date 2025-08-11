import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import date

st.set_page_config(layout="wide")
st.title("Dashboard de Mantenimiento - Sierras Disco y Cinta")

# Cargar los archivos Excel
df_disco = pd.read_excel('SIERRA disco, C-62.xlsx', engine='openpyxl')
df_cinta = pd.read_excel('SIERRA cinta, C-14.xlsx', engine='openpyxl')

# Añadir columna que indica la máquina
df_disco['Maquina'] = 'Sierra Disco'
df_cinta['Maquina'] = 'Sierra Cinta'

# Fusionar los DataFrames
df = pd.concat([df_disco, df_cinta], ignore_index=True)

# Convertir fechas
df['Inicio real'] = pd.to_datetime(df['Inicio real'], errors='coerce')
df['Fin real'] = pd.to_datetime(df['Fin real'], errors='coerce')
df['Mes'] = df['Inicio real'].dt.to_period('M').astype(str)

# Determinar si la intervención está cerrada usando 'Fin real'
df['Intervencion Cerrada'] = pd.notnull(df['Fin real'])

# Filtrar intervenciones cerradas
df_validas = df[df['Intervencion Cerrada']].copy()
df_validas['Carga real'] = pd.to_numeric(df_validas['Carga real'], errors='coerce')

# Estimar tipo de intervención desde 'Informe'
def estimar_tipo(row):
    texto = str(row['Informe']).lower()
    if 'preventivo' in texto:
        return 'Preventivo'
    elif 'correctivo' in texto or 'falla' in texto or 'reparación' in texto:
        return 'Correctivo'
    else:
        return 'Otro'

df_validas['Tipo estimado'] = df_validas.apply(estimar_tipo, axis=1)

# Filtro de fechas (corregido)
min_fecha = df['Inicio real'].min().date()
max_fecha = df['Inicio real'].max().date()
fecha_inicio, fecha_fin = st.slider("Selecciona el rango de fechas", min_value=min_fecha, max_value=max_fecha, value=(min_fecha, max_fecha), format="YYYY-MM-DD")
fecha_inicio = pd.to_datetime(fecha_inicio)
fecha_fin = pd.to_datetime(fecha_fin)

df_filtrado = df[(df['Inicio real'] >= fecha_inicio) & (df['Inicio real'] <= fecha_fin)]
df_validas_filtrado = df_validas[(df_validas['Inicio real'] >= fecha_inicio) & (df_validas['Inicio real'] <= fecha_fin)]

# 1. Frecuencia de intervenciones por máquina
fig1 = px.histogram(df_filtrado, x='Maquina', color='Maquina', title='Frecuencia de intervenciones por máquina', text_auto=True)
fig1.update_traces(customdata=df_filtrado['Maquina'], hovertemplate='<b>Máquina:</b> %{customdata}<br><b>Intervenciones:</b> %{y}')
st.plotly_chart(fig1, use_container_width=True)

# 2. Tipos de intervención estimados
fig2 = px.histogram(df_validas_filtrado, x='Tipo estimado', color='Maquina', barmode='group',
                    title='Tipos de intervención estimados', text_auto=True)
fig2.update_traces(customdata=df_validas_filtrado['Maquina'], hovertemplate='<b>Tipo:</b> %{x}<br><b>Máquina:</b> %{customdata}<br><b>Intervenciones:</b> %{y}')
st.plotly_chart(fig2, use_container_width=True)

# 3. Duración promedio por máquina
duracion_promedio = df_validas_filtrado.groupby('Maquina')['Carga real'].mean().reset_index()
fig3 = px.bar(duracion_promedio, x='Maquina', y='Carga real', color='Maquina',
              title='Duración promedio de intervenciones', text_auto=True)
fig3.update_traces(customdata=duracion_promedio['Maquina'], hovertemplate='<b>Máquina:</b> %{customdata}<br><b>Duración promedio:</b> %{y:.2f} horas')
st.plotly_chart(fig3, use_container_width=True)

# 4. Tendencia mensual de intervenciones con línea de promedio
tendencia = df_filtrado.groupby(['Mes', 'Maquina']).size().reset_index(name='Cantidad')
promedios = tendencia.groupby('Maquina')['Cantidad'].mean().reset_index()
promedios_dict = dict(zip(promedios['Maquina'], promedios['Cantidad']))

color_map = px.colors.qualitative.Plotly
maquinas = tendencia['Maquina'].unique()
color_dict = {maquinas[i]: color_map[i % len(color_map)] for i in range(len(maquinas))}

fig4 = px.line(tendencia, x='Mes', y='Cantidad', color='Maquina',
               title='Tendencia mensual de intervenciones con línea de promedio')
fig4.update_traces(mode='lines+markers', customdata=tendencia['Maquina'],
                   hovertemplate='<b>Mes:</b> %{x}<br><b>Máquina:</b> %{customdata}<br><b>Cantidad:</b> %{y}')

for maquina in maquinas:
    promedio = promedios_dict[maquina]
    meses_maquina = tendencia[tendencia['Maquina'] == maquina]['Mes']
    fig4.add_trace(go.Scatter(
        x=meses_maquina,
        y=[promedio] * len(meses_maquina),
        mode='lines',
        name=f'Promedio {maquina}',
        line=dict(dash='dash', color=color_dict[maquina]),
        customdata=[maquina] * len(meses_maquina),
        hovertemplate='<b>Máquina:</b> %{customdata}<br><b>Promedio mensual:</b> %{y:.2f}'
    ))

if not tendencia.empty:
    max_row = tendencia.loc[tendencia['Cantidad'].idxmax()]
    fig4.add_annotation(x=max_row['Mes'], y=max_row['Cantidad'],
                        text='Pico de intervenciones', showarrow=True, arrowhead=1)
st.plotly_chart(fig4, use_container_width=True)

# 5. Total de horas perdidas por máquina
horas_perdidas = df_validas_filtrado.groupby('Maquina')['Carga real'].sum().reset_index()
fig5 = px.bar(horas_perdidas, x='Maquina', y='Carga real', color='Maquina',
              title='Total de horas perdidas por máquina', text_auto=True)
fig5.update_traces(customdata=horas_perdidas['Maquina'], hovertemplate='<b>Máquina:</b> %{customdata}<br><b>Horas perdidas:</b> %{y:.2f}')
st.plotly_chart(fig5, use_container_width=True)

# 6. Comparación porcentual entre máquinas
total_intervenciones = df_validas_filtrado['Maquina'].value_counts(normalize=True).reset_index()
total_intervenciones.columns = ['Maquina', 'Porcentaje']
fig6 = px.pie(total_intervenciones, names='Maquina', values='Porcentaje',
              title='Distribución porcentual de intervenciones por máquina',
              hole=0.4)
fig6.update_traces(customdata=total_intervenciones['Maquina'], hovertemplate='<b>Máquina:</b> %{customdata}<br><b>Porcentaje:</b> %{percent}')
st.plotly_chart(fig6, use_container_width=True)
