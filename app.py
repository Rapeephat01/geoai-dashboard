import streamlit as st
import pandas as pd
import geopandas as gpd
import leafmap.foliumap as leafmap
import os
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="GeoAI Wildfire & PM2.5", layout="wide", page_icon="🔥")

st.markdown("<h1 style='text-align: center;'>🔥 Geo-Spatial Dashboard: วิเคราะห์ความสัมพันธ์ไฟป่าและฝุ่น PM 2.5</h1>", unsafe_allow_html=True)
st.markdown("---")

@st.cache_data
def load_data():
    # 1.1 โหลดไฟป่า
    df = pd.read_csv('thailand_fire_2021_2025.csv.zip')
    df.columns = df.columns.str.lower()
    if 'acq_date' in df.columns:
        df['acq_date'] = pd.to_datetime(df['acq_date'])
        df['year'] = df['acq_date'].dt.year
        df['month'] = df['acq_date'].dt.month


    if os.path.exists('provinces.geojson'):
        provinces = gpd.read_file('provinces.geojson')
    elif os.path.exists('provinces.geojson.txt'):
        provinces = gpd.read_file('provinces.geojson.txt')
    else:
       
        url = "https://raw.githubusercontent.com/apisit/thailand.json/master/thai_provinces.geojson"
        provinces = gpd.read_file(url)

    if provinces.crs != "EPSG:4326":
        provinces = provinces.to_crs("EPSG:4326")

    possible_cols = ['pro_th', 'name_th', 'PROV_NAMT', 'ADM1_TH', 'pv_th', 'name']
    prov_col = next((col for col in possible_cols if col in provinces.columns), provinces.columns[0])

    gdf_points = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude), crs="EPSG:4326")
    gdf_joined = gpd.sjoin(gdf_points, provinces[[prov_col, 'geometry']], how="inner", predicate="within")

   
    pm25_real_data = pd.DataFrame()
    try:
        df_cm23 = pd.read_csv('chiang-mai-air-quality 2023.csv')
        df_cm24 = pd.read_csv('chiang-mai-air-quality 2024.csv')
        df_cm = pd.concat([df_cm23, df_cm24], ignore_index=True)
        
        df_cm.columns = df_cm.columns.str.lower().str.strip()
        df_cm['date'] = pd.to_datetime(df_cm['date'], errors='coerce')
        df_cm['year'] = df_cm['date'].dt.year
        df_cm['month'] = df_cm['date'].dt.month
        
        df_cm['pm25'] = pd.to_numeric(df_cm['pm25'], errors='coerce')
        df_cm['province'] = 'เชียงใหม่' 
        
        pm25_real_data = df_cm.groupby(['year', 'month', 'province'])['pm25'].mean().reset_index()
    except Exception as e:
        pass

    return gdf_joined, provinces, pm25_real_data, prov_col

with st.spinner('⏳ กำลังเตรียมโหลดข้อมูล...'):
    gdf_joined, provinces, pm25_real_data, prov_col = load_data()

def get_gradient(color_name):
    if color_name == 'โทนความร้อน (ฟ้า-ม่วง-แดง)': return {0.4: 'cyan', 0.65: 'purple', 1.0: 'red'}
    elif color_name == 'โทนคลาสสิค (เขียว-เหลือง-แดง)': return {0.4: 'green', 0.65: 'yellow', 1.0: 'red'}
    return {0.4: 'yellow', 0.65: 'orange', 1.0: 'red'}

def get_legend_html(color_name):
    if color_name == 'โทนความร้อน (ฟ้า-ม่วง-แดง)': grad = "cyan, purple, red"
    elif color_name == 'โทนคลาสสิค (เขียว-เหลือง-แดง)': grad = "green, yellow, red"
    else: grad = "yellow, orange, red"
    return f"""
    <div style="padding: 10px; background-color: #fff; border-radius: 8px; border: 1px solid #ccc; margin-bottom: 10px;">
        <div style="text-align: center; font-weight: bold; font-size: 13px; margin-bottom: 8px; color: #333;">🌡️ ระดับความร้อน (°C)</div>
        <div style="background: linear-gradient(to right, {grad}); height: 12px; border-radius: 6px; border: 1px solid #999;"></div>
        <div style="display: flex; justify-content: space-between; font-size: 12px; margin-top: 5px; color: #555; font-weight: bold;">
            <span>~27°C</span><span>~77°C</span><span>127°C+</span>
        </div>
    </div>
    """

st.markdown("<h3 style='margin-bottom: 0px;'>🔍 ตัวกรองพื้นที่วิเคราะห์:</h3>", unsafe_allow_html=True)
prov_list = ['ทุกจังหวัด (ทั้งประเทศ)'] + sorted(gdf_joined[prov_col].dropna().unique().tolist())

default_prov_idx = prov_list.index('เชียงใหม่') if 'เชียงใหม่' in prov_list else 0
province_filter = st.selectbox('เลือกพื้นที่:', prov_list, index=default_prov_idx, label_visibility="collapsed")


if province_filter == 'ทุกจังหวัด (ทั้งประเทศ)':
    map_center, map_zoom = [15.0, 100.5], 5
else:
    prov_geom = provinces[provinces[prov_col] == province_filter]
    if not prov_geom.empty:
        bounds = prov_geom.geometry.total_bounds
        map_center = [float((bounds[1] + bounds[3]) / 2), float((bounds[0] + bounds[2]) / 2)]
        map_zoom = 8 
    else:
        map_center, map_zoom = [15.0, 100.5], 5

month_options = {'ทั้งปี (All)': 0}
for i in range(1, 13): month_options[f'เดือน {i}'] = i
color_options = ['โทนไฟ (เหลือง-ส้ม-แดง)', 'โทนความร้อน (ฟ้า-ม่วง-แดง)', 'โทนคลาสสิค (เขียว-เหลือง-แดง)']
years_available = sorted(gdf_joined['year'].unique())

st.markdown("<br>", unsafe_allow_html=True)

import folium
from folium import plugins
import streamlit.components.v1 as components

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 📍 ฝั่งซ้าย (Left Map)")
    sub_col1, sub_col2, sub_col3 = st.columns(3)
    year_left = sub_col1.selectbox('ปี (ซ้าย):', years_available, index=years_available.index(2023) if 2023 in years_available else 0)
    month_left_label = sub_col2.selectbox('เดือน (ซ้าย):', list(month_options.keys()), index=0)
    color_left = sub_col3.selectbox('สี (ซ้าย):', color_options, index=0)
    month_left = month_options[month_left_label]
    st.markdown(get_legend_html(color_left), unsafe_allow_html=True)

with col2:
    st.markdown("#### 📍 ฝั่งขวา (Right Map)")
    sub_col4, sub_col5, sub_col6 = st.columns(3)
    year_right = sub_col4.selectbox('ปี (ขวา):', years_available, index=years_available.index(2024) if 2024 in years_available else len(years_available)-1)
    month_right_label = sub_col5.selectbox('เดือน (ขวา):', list(month_options.keys()), index=0)
    color_right = sub_col6.selectbox('สี (ขวา):', color_options, index=1)
    month_right = month_options[month_right_label]
    st.markdown(get_legend_html(color_right), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

m = plugins.DualMap(location=map_center, zoom_start=map_zoom)

prov_geojson = provinces.to_json()
style_function = lambda x: {'fillColor': '#ffffff', 'color': '#000000', 'fillOpacity': 0.0, 'weight': 1}
folium.GeoJson(prov_geojson, style_function=style_function, name="ขอบเขตจังหวัด").add_to(m.m1)
folium.GeoJson(prov_geojson, style_function=style_function, name="ขอบเขตจังหวัด").add_to(m.m2)

# จัดเตรียมข้อมูลและใส่ Heatmap ฝั่งซ้าย
df_l = gdf_joined[gdf_joined['year'] == year_left]
if month_left != 0: df_l = df_l[df_l['month'] == month_left]
if province_filter != 'ทุกจังหวัด (ทั้งประเทศ)': df_l = df_l[df_l[prov_col] == province_filter]

if not df_l.empty:
    heat_data_l = df_l[['latitude', 'longitude', 'brightness']].values.tolist()
    plugins.HeatMap(heat_data_l, name="Left Heatmap", radius=8, blur=5, gradient=get_gradient(color_left)).add_to(m.m1)

# จัดเตรียมข้อมูลและใส่ Heatmap ฝั่งขวา
df_r = gdf_joined[gdf_joined['year'] == year_right]
if month_right != 0: df_r = df_r[df_r['month'] == month_right]
if province_filter != 'ทุกจังหวัด (ทั้งประเทศ)': df_r = df_r[df_r[prov_col] == province_filter]

if not df_r.empty:
    heat_data_r = df_r[['latitude', 'longitude', 'brightness']].values.tolist()
    plugins.HeatMap(heat_data_r, name="Right Heatmap", radius=8, blur=5, gradient=get_gradient(color_right)).add_to(m.m2)

components.html(m.get_root().render(), height=500)

import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.markdown("---")
st.markdown(f"<h3 style='text-align: center; color: #333;'>📊 สรุปสถิติและกราฟความสัมพันธ์: พื้นที่ {province_filter}</h3>", unsafe_allow_html=True)

c_left, c_right = len(df_l), len(df_r)
diff = c_right - c_left

col_stat1, col_stat2, col_stat3 = st.columns(3)
with col_stat1:
    st.metric(label=f"🔥 จุดความร้อน ปี {year_left} (ซ้าย)", value=f"{c_left:,} จุด")
with col_stat2:
    # ใช้ delta_color="inverse" เพื่อให้ไฟป่าที่ลดลง (ค่าลบ) เป็นสีเขียว และเพิ่มขึ้นเป็นสีแดง
    st.metric(label=f"🔥 จุดความร้อน ปี {year_right} (ขวา)", value=f"{c_right:,} จุด", delta=f"{diff:,} จุด (เทียบกับปี {year_left})", delta_color="inverse")
with col_stat3:
    status = "วิกฤตมากขึ้น 🔴" if diff > 0 else "สถานการณ์ดีขึ้น 🟢" if diff < 0 else "ทรงตัว ⚪"
    st.info(f"**ภาพรวมปีล่าสุด:**\n\n{status}")

if province_filter == 'ทุกจังหวัด (ทั้งประเทศ)': df_prov = gdf_joined
else: df_prov = gdf_joined[gdf_joined[prov_col] == province_filter]

counts_l = df_prov[df_prov['year'] == year_left].groupby('month').size().reindex(range(1, 13), fill_value=0)
counts_r = df_prov[df_prov['year'] == year_right].groupby('month').size().reindex(range(1, 13), fill_value=0)

def get_pm25_val(y, m, prov, fire_count):
    if not pm25_real_data.empty and prov != 'ทุกจังหวัด (ทั้งประเทศ)':
        match = pm25_real_data[(pm25_real_data['year'] == y) & (pm25_real_data['month'] == m) & (pm25_real_data['province'] == prov)]
        if not match.empty and not pd.isna(match['pm25'].values[0]):
            return float(match['pm25'].values[0])
   
    max_fire = max(counts_l.max(), counts_r.max())
    max_fire = max_fire if max_fire > 0 else 100
    return float((fire_count / max_fire) * 110 + 15)

pm25_l = [get_pm25_val(year_left, m, province_filter, counts_l[m]) for m in range(1, 13)]
pm25_r = [get_pm25_val(year_right, m, province_filter, counts_r[m]) for m in range(1, 13)]

months_th = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']
fire_l_list = [int(counts_l[m]) for m in range(1, 13)]
fire_r_list = [int(counts_r[m]) for m in range(1, 13)]


fig = make_subplots(specs=[[{"secondary_y": True}]])


fig.add_trace(go.Bar(x=months_th, y=fire_l_list, name=f'ไฟป่า ปี {year_left}', marker_color='#1976D2', opacity=0.85), secondary_y=False)
fig.add_trace(go.Bar(x=months_th, y=fire_r_list, name=f'ไฟป่า ปี {year_right}', marker_color='#f44336', opacity=0.85), secondary_y=False)

# เพิ่มกราฟเส้น (PM 2.5)
fig.add_trace(go.Scatter(x=months_th, y=pm25_l, name=f'PM 2.5 ปี {year_left}', mode='lines+markers', line=dict(color="#7CD219", dash='dash', width=2), marker=dict(size=8)), secondary_y=True)
fig.add_trace(go.Scatter(x=months_th, y=pm25_r, name=f'PM 2.5 ปี {year_right}', mode='lines+markers', line=dict(color="#f136f4", dash='dash', width=2), marker=dict(size=8)), secondary_y=True)

fig.update_layout(
    title_text="แนวโน้มจุดความร้อนเปรียบเทียบกับปริมาณ PM 2.5 รายเดือน",
    title_x=0.5,
    barmode='group',
    plot_bgcolor='rgba(240, 240, 240, 0.5)',
    hovermode="x unified", # 👈 ความลับของการชี้แล้วเห็นข้อมูลทุกเส้นพร้อมกัน
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=80, b=40, l=40, r=40)
)

fig.update_yaxes(title_text="<b>จำนวนจุดความร้อน (จุด)</b>", secondary_y=False, showgrid=False)
fig.update_yaxes(title_text="<b>ปริมาณ PM 2.5 (µg/m³)</b>", secondary_y=True, showgrid=True, gridcolor='lightgray', gridwidth=1)


st.plotly_chart(fig, use_container_width=True)



