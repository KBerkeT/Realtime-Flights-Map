import requests
import pandas as pd
from bokeh.plotting import figure, curdoc
from bokeh.models import LabelSet, ColumnDataSource, DataTable,  TableColumn, Label,Panel, Tabs, CDSView, BooleanFilter
from bokeh.tile_providers import get_provider, OSM
import numpy as np
from bokeh.layouts import Row, layout


#Nokta koordinatları dönüştürmek için fonksiyon
def wgs84_web_mercator_point(lon,lat):
    k = 6378137
    x= lon * (k * np.pi/180.0)
    
    y= np.log(np.tan((90 + lat) * np.pi/360.0)) * k
    return x,y

#Data içindeki koordinatları dönüştürmek için fonksiyon
def wgs84_to_web_mercator(df, lon, lat):
    """Converts decimal longitude/latitude to Web Mercator format"""
    k = 6378137
    df["X"] = df[lon] * (k * np.pi/180.0)
    df["Y"] = np.log(np.tan((90 + df[lat]) * np.pi/360.0)) * k
    return df

#Grafik oluşturmak için ülke isimleri ve hangi ülkenin kaç uçağı olduğunu gösteren bir DataFrame oluşturan fonksiyon
def country_plane(data,country):
    
    countrys = list(set(data[country]))
    planes = []
    for i in countrys: 
        counter = 0 
        for j in data[country]:
            if i == j:
                counter+=1
        planes.append(counter)
    
    countrys.append("Toplam")
    planes.append(sum(planes))
    df = pd.DataFrame({"Country":countrys,"planes":planes})
    df.sort_values("planes",ascending=False, inplace=True)
    return df

#Requestle çekilen veriyi DataFrame kullanarak uygun formata getirmek için fonksiyon
def df_format(response):
    
    #Sütun isimleri 
    col_name = ['icao24','callsign','origin_country','time_position','last_contact',
            'long','lat','baro_altitude','on_ground','velocity',       
            'true_track','vertical_rate','sensors','geo_altitude','squawk','spi',
            'position_source']
    
    #Pandas.DataFrame kullanılarak veri düzenlendi
    df = pd.DataFrame(response) #Yanıt içindeki "states" df ye tanımlandı
    df = df.loc[:,0:16] #df tümsatırları alındı ve 17 sütuna ayrıldı
    df.columns = col_name #Tanımlanan sütun isimleri eklendi
    wgs84_to_web_mercator(df,"long","lat") #wgs84 ten mercator dönüşümü yapıldı. X ve Y sütunları
    df = df.fillna(-1) #NaN değerleri No Data olarak değiştirildi.
    df["rot_angle"] = (df["true_track"]*-1)+45 #icon açısı için rot_angle oluşturuldu.
    df["url"] = icon_url #icon tanımlandı
    list_str = []
    for i in df["baro_altitude"]:
        list_str.append(str(i)+" m")
    df["str_altitude"] = list_str
    return df

def create_fig(weight, height, x_range, y_range):
	p = figure(plot_width = weight, plot_height = height,
            x_range=x_range,y_range=y_range,
            x_axis_type="mercator",y_axis_type="mercator", sizing_mode="scale_width",
            tooltips=[("Call Sign","@callsign"),("Country","@origin_country"),("Barometric Altitude", "@str_altitude")]
            )
	return p

def create_icon(fig, source):
	fig.circle(x="X", y="Y", size=10, line_color="red", fill_color="red", 
	fill_alpha=0, line_width=0, source=source)
	fig.image_url(url="url", x="X", y="Y", anchor="center", angle_units="deg",
				angle="rot_angle", h_units="screen", w_units="screen",
				h=IMAGE_H, w=IMAGE_W, source=url_source)

#####################
def altitude_filter(source,min_altitude,max_altitude):
    alt_filter = [True if int(alti) > min_altitude and int(alti) <= max_altitude else False for alti in source.data["baro_altitude"]]
    return alt_filter

def create_circle(p,size,color,source,view,legend_label):
    p.circle(x="X",y="Y",size=size,fill_color=color,line_color=color,legend_label=legend_label,view=view,fill_alpha=0.6,line_width=3,source=source) 
###################

def update():
	response = requests.get(url).json() 
	response = response["states"]      
	url_data = df_format(response) #Uçuş haritası için gerekli format  
	flight_df = country_plane(url_data,"origin_country") #Grafik için gerekli format

	for i in range(len(alti_list)):
		alti_filter = altitude_filter(url_source, alti_list[i], alti_list[i] + 2500)
		view = CDSView(source = url_source,filters = [BooleanFilter(alti_filter)])
		create_circle(p_filt, 4, color_list[i], url_source, view, f"{alti_list[i]}-{alti_list[i]+2500} m")

	#url_source verilerini güncellemek için .stream kullanılıyor
	n_roll=len(url_data.index)
	url_source.stream(url_data.to_dict(orient="list"),n_roll)

	#flight_source verilerini güncellemek için .stream kullanılıyor. Veri kümesi içinde sadece değişen hücreleri güncelliyor.
	n_roll=len(flight_df.index)
	flight_source.stream(flight_df.to_dict(orient="list"),n_roll)

#API için kullanıcı adı ve şifre, çalışma alanı sınırları - Ücretsiz OpenSkyNetwork hesabı 
user_name = "*****"
password = "*****"

#Kod içinde sınır için kullanılan sayısal veriler.
#Uçuş sınırları
lon_min,lat_min = 25,35 
lon_max,lat_max = 45,45
#Harita boyutları
FIGURE_W = 400
FIGURE_H = 200
#İkon boyutları
IMAGE_H = 10
IMAGE_W = 10

#https://opensky-network.org/api/states/all?lamin={}&lomin={}&lamax={}&lomax={}
url = "https://{}:{}@opensky-network.org/api/states/all?lamin={}&lomin={}&lamax={}&lomax={}".format(user_name,password,lat_min,lon_min,lat_max,lon_max)
icon_url = "https://iconvulture.com/wp-content/uploads/2017/12/plane.svg?1648292982753" 

#Nokta koordinat dönüşümü icon için
xy_min=wgs84_web_mercator_point(lon_min,lat_min)
xy_max=wgs84_web_mercator_point(lon_max,lat_max)

x_range = [xy_min[0],xy_max[0]]
y_range = [xy_min[1],xy_max[1]]

doc = curdoc()

url_source = ColumnDataSource({
    	'icao24':[],'callsign':[],'origin_country':[],
    	'time_position':[],'last_contact':[],'long':[],'lat':[],
    	'baro_altitude':[],'str_altitude':[],'on_ground':[],'velocity':[],'true_track':[],
    	'vertical_rate':[],'sensors':[],'geo_altitude':[],'squawk':[],'spi':[],
    	'position_source':[],'X':[],'Y':[],'rot_angle':[],'url':[] })

flight_source = ColumnDataSource({"Country":[],"planes":[]})

doc.add_periodic_callback(update, 5000)

p = create_fig(FIGURE_W, FIGURE_H, x_range, y_range)
create_icon(p, url_source)
labels = LabelSet(x = "X", y = "Y", text ="callsign", level="glyph",  
		x_offset=2, y_offset=2, source=url_source, render_mode='canvas',
		background_fill_color='white',text_font_size="5pt")
	
osmHarita = get_provider(OSM) #Altlık 
p.add_tile(osmHarita) #Altlık ekleme
p.add_layout(labels)  #Çağrı adları yazan label ekleniyor

p_filt = create_fig(FIGURE_W, FIGURE_H, x_range, y_range)
alti_list = [0, 2500, 5000, 7500, 10000, 12500]
color_list = ["aqua","blue","green","yellow","orange","red"]

p_filt.add_tile(osmHarita)

tab1 = Panel(child=p, title="Map")
tab2 = Panel(child=p_filt, title="Filter")
tab = Tabs(tabs=[tab1, tab2])

#Veri tablosu oluşturuluyor
columns = [TableColumn(field = "Country", title="Countrys"),TableColumn(field="planes",title="Planes")] #Veri tablosunun sütun isimleri 
data_table = DataTable(source=flight_source, columns=columns)

lay = Row(tab, data_table)
doc.add_root(lay)
# Server çalıştırmak için bokeh serve file_name.py
