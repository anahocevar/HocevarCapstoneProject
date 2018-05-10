from flask import Flask, render_template, request, redirect, url_for

from bokeh.layouts import row, widgetbox, column, layout, gridplot
from bokeh.models import GeoJSONDataSource, CustomJS, Slider, HoverTool, DateSlider, Select, LinearColorMapper, ColorBar
from bokeh.plotting import figure, show, ColumnDataSource, curdoc
from bokeh.embed import components
from bokeh.palettes import brewer

import datetime as dt
import pandas as pd
import numpy as np
import pickle

app = Flask(__name__)

app.vars={}

@app.route('/', methods=['GET'])
def bkapp_page():
   
    ###-----------------------------------------------------------------------###
    ###------------------------PREPARING DATA---------------------------------###
    ### This section contains getting and preparing data for this plot------  ###
    ###-----------------------------------------------------------------------###

    ### Load dataset rat interventions
    bait_interventions_to_save = pd.read_pickle('bait_interventions_to_save_pitch_night.pickle')
    ### Load indices of rows for each month for bait dataset
    indices_bait_df = pd.read_pickle('development/indices_bait_df_pitch_night.pickle')    #has 2 columns: 'from_index' and 'to_index'
    ### Load dataset rat sighting
    dataset_sightings_locations_to_save = pd.read_pickle('development/dataset_sightings_locations_to_save_pitch_night.pickle')
    ### Load indices of rows for each month for sightings dataset
    indices_sight_df = pd.read_pickle('development/indices_sight_df_pitch_night.pickle')    #has 2 columns: 'from_index' and 'to_index'

    ### Load dataset by zipcodes
    by_zipcodes_df = pd.read_pickle('development/dataset_by_zipcodes_pitch_night.pickle')
    
    ### PREDICTIONS datasets
    df = pd.read_pickle('development/locations_prediction_df_pitch_night.pickle')
    prophet_fit_all_nyc = pd.read_pickle('development/prophet_fit_all_nyc_pitch_night.pickle')    
    prophet_prediction_all_nyc = pd.read_pickle('development/prophet_prediction_all_nyc_pitch_night.pickle')    
        
    ### Read the nyc map data
    nyc_df = pd.read_pickle('development/nyc_converted_to_save.pickle')
    nyc_by_zips = pd.read_pickle('development/dataset_map_by_zipcodes_pitch_night.pickle')
    zip_hm = pd.read_pickle('development/zip_heatmaps_pitch_night.pickle')


    ### Read existing year-month strings in dataset
    with open('development/timepoints_pitch_night.pickle', "rb") as f:
        timepoints = pickle.load(f)
    timepoints = timepoints[:-1]
    
    ### list of zipcodes in dataset
    with open('development/all_zips.pickle', "rb") as f:
        all_zips = pickle.load(f)
    
    ### Read predicted months
    with open('development/predicted_months_pitch_night.pickle', "rb") as f:
        predicted_months = pickle.load(f)    
    
    ### prepare data for bokeh
    bait_source = ColumnDataSource(bait_interventions_to_save)
    indices_bait_source = ColumnDataSource(indices_bait_df)
    sight_source = ColumnDataSource(dataset_sightings_locations_to_save)
    indices_sight_source = ColumnDataSource(indices_sight_df)
    nyc_source = ColumnDataSource(nyc_df)
    timepoints_cds = ColumnDataSource(pd.DataFrame({'timepoints':timepoints}))
    predicted_months_cds = ColumnDataSource(pd.DataFrame({'predicted_months':predicted_months}))
    by_zipcodes_source = ColumnDataSource(by_zipcodes_df)
    nyc_by_zips_source = ColumnDataSource(nyc_by_zips)
    zip_hm_first = ColumnDataSource(zip_hm.loc[:,['ZIPCODE','x','y','sightings']])
    zip_hm_original = ColumnDataSource(zip_hm)

   
    ### bokeh data source for initial plot rendered:
    first_source_bait = ColumnDataSource(bait_interventions_to_save.iloc[indices_bait_df['from_index'][51]:indices_bait_df['to_index'][51],:])
    first_source_sight = ColumnDataSource(dataset_sightings_locations_to_save.iloc[indices_sight_df['from_index'][51]:indices_sight_df['to_index'][51],:])
    
    
    ###-----------------------------------------------------------------------###
    ###----------------------GRAPHICAL USER INTERFACE-------------------------###
    ### This code defines the Bokeh controls that are used for the user       ###
    ### interface. ---------------------------------------------------------- ### 
    ###-----------------------------------------------------------------------###
    
    ### Initialize plot figure
    p = figure(x_range=(-74.2, -73.7), y_range=(40.53, 40.915), tools= 'box_zoom,pan,save,reset', active_drag="box_zoom",
               min_border_right = 40, min_border_top = 5, min_border_bottom = 5, border_fill_color = "black",
               background_fill_color = "black", toolbar_location="left")
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    p.axis.visible = False
    p.outline_line_color = "black"
 
    ###-----------------------------------------------------------------------###
    ###------------------------PREDICTED locations----------------------------###
    ###-------------------------heatmap---------------------------------------###
    ###-----------------------------------------------------------------------###
     
    
    colors = ['#000000'] + brewer["Reds"][9]
    binsize = 0.5/80
    hm_source = ColumnDataSource(pd.read_pickle('development/df_mock_pitch_practice.pickle'))    
#     hm_source = ColumnDataSource(df)
    hm_source_original = ColumnDataSource(df)
    ## not nomalized count
    mapper = LinearColorMapper(palette=colors, low=df.rat_count.min(), high=df.rat_count.max())
    prediction_location = p.rect(x="level_0", y="level_1", width=binsize, height=binsize,
           source=hm_source,
           fill_color={'field': 'start', 'transform': mapper},
           line_color=None) 

    ###-----------------------------------------------------------------------###
    ###---------------------------NYC map-------------------------------------###
    ###------------------------and events from data---------------------------###
    ###-----------------------------------------------------------------------###
       
    
    ### Add nyc map
    p.patches('x', 'y', source=nyc_source, color='black', line_width=1, fill_color={'field': 'colors'}, fill_alpha = 0.4)
    
    ### Add my bait points
    baits = p.circle('LONGITUDE', 'LATITUDE', source=first_source_bait, fill_color='#4dc6e0', line_color = '#4dc6e0', line_width=3, line_alpha=0.6, legend="Rat Interventions")
    ### Add my sights points
    sights = p.circle('LONGITUDE', 'LATITUDE', source=first_source_sight, fill_color = '#d96c82',line_color = '#d96c82',line_width=3, line_alpha=0.6, legend="Rat Sightings")
    
    p.legend.location = "top_left"
    p.legend.label_text_color = 'white'
    p.legend.border_line_color = "white"
    p.legend.background_fill_color = "black"
    
    ### Add slider
    date_slider = DateSlider(title="Date", start=dt.date(2010, 1, 1), end=dt.date(2018, 9, 1),value=dt.date(2014, 4, 1), step=1, format = "%B %Y")
        
    ### Add hovers
    bait_hover = HoverTool(tooltips = """
    <div>
        <div>
            <span style="font-size: 14px; font-weight:bold; color: #00BFFF">Location:</span> <span style="font-size: 15px; color: #000000">@HOUSE_NUMBER @STREET_NAME</span><br>
            <span style="font-size: 14px; font-weight:bold; color: #00BFFF;">Zip Code:</span> <span style="font-size: 15px; color: #000000"> @ZIP_CODE </span><br>
            <span style="font-size: 14px; font-weight:bold; color: #00BFFF;">Intervention Date: </span> <span style="font-size: 15px; color: #000000">@Inspection_Date</span><br>
            <span style="font-size: 14px; font-weight:bold; color: #00BFFF;">Intervention Type: </span> <span style="font-size: 15px; color: #000000">@RESULT</span>
        </div>
    </div>
    """, renderers=[baits]) 
    p.add_tools(bait_hover)
    
    sight_hover = HoverTool(tooltips = """
    <div>
        <div>
            <span style="font-size: 14px; font-weight:bold; color: #F08080">Location:</span> <span style="font-size: 15px; color: #000000">@ADDRESS</span><br>
            <span style="font-size: 14px; font-weight:bold; color: #F08080;">Zip Code:</span> <span style="font-size: 15px; color: #000000"> @ZIP_CODE </span><br>
            <span style="font-size: 14px; font-weight:bold; color: #F08080;">Rat Sighting Date: </span> <span style="font-size: 15px; color: #000000">@Sighting_Date</span>
        </div>
    </div>
    """, renderers=[sights])
    p.add_tools(sight_hover)
    
    
    prediction_hover = HoverTool(tooltips = """
    <div>
        <div>
            <span style="font-size: 14px; font-weight:bold; color: #F08080">Longitude:</span> <span style="font-size: 15px; color: #000000">@level_0</span><br>
            <span style="font-size: 14px; font-weight:bold; color: #F08080;">Latitude:</span> <span style="font-size: 15px; color: #000000"> @level_1 </span><br>
            <span style="font-size: 14px; font-weight:bold; color: #F08080;">Predicted monthly sightings: </span> <span style="font-size: 15px; color: #000000">@start</span>
        </div>
    </div>
    """, renderers=[prediction_location])
    p.add_tools(prediction_hover)
    
    
    ### Add a Zip Code selection option
    zip_select = Select(title="Selected Zipcode:", value="all zipcodes", options= all_zips)
    
    
    ###-----------------------------------------------------------------------###
    ###------------------------PLOT of whole----------------------------------###
    ###----------------------city sightings numbers---------------------------###
    ###-----------------------------------------------------------------------###
    
    fit_source = ColumnDataSource(prophet_fit_all_nyc)
    prediction_source = ColumnDataSource(prophet_prediction_all_nyc)

    p_right = figure(title = 'CITY-WIDE MONTHLY PREDICTIONS',tools= 'box_zoom,pan,save,reset', min_border_top = 250, min_border_left = 100, border_fill_color = "black",
               background_fill_color = "black", width = 600, height = 550, active_drag="box_zoom", x_axis_type="datetime")
    
    # interval shading glyph:
    lowerband = prophet_prediction_all_nyc['yhat_lower'].values
    upperband = prophet_prediction_all_nyc['yhat_upper'].values
    band_x = np.append(prophet_prediction_all_nyc['ds'].values, prophet_prediction_all_nyc['ds'].values[::-1])
    band_y = np.append(lowerband, upperband[::-1])
    p_right.patch(band_x, band_y, color='white', fill_alpha=0.5, alpha = 0.5)

    p_right.line(x = 'ds', y = 'y', source = fit_source, color = '#d96c82', line_width=2.6, legend = 'monthly rat sightings')
    p_right.circle(x = 'ds', y = 'y', source = fit_source, color = '#d96c82', size = 7, alpha = 0.5, legend = 'monthly rat sightings')

    p_right.line(x = 'ds', y = 'yhat', source = prophet_fit_all_nyc, line_width=2, color = 'white', legend = 'FBprophet fit/prediction')
    p_right.circle(x = 'ds', y = 'yhat', source = prophet_fit_all_nyc, color = 'white', size = 5, alpha = 0.5, legend = 'FBprophet fit/prediction')
    p_right.line(x = 'ds', y = 'yhat', source = prophet_prediction_all_nyc, line_width=2, color = 'white', line_dash="4 4")
    p_right.circle(x = 'ds', y = 'yhat', source = prophet_prediction_all_nyc, size = 5, color = 'white', alpha = 0.5, line_dash="4 4")

    p_right.line([prophet_fit_all_nyc.iloc[-1,0], prophet_prediction_all_nyc.iloc[0,0]], 
           [prophet_fit_all_nyc.iloc[-1,2], prophet_prediction_all_nyc.iloc[0,1]], line_dash="4 4", 
           line_width=2, color='white')

    p_right.legend.location = "top_left"
    p_right.xaxis.major_label_text_font_size = "14pt"
    p_right.yaxis.major_label_text_font_size = "14pt"
    p_right.title.text_font_size = '16pt'
    p_right.legend.label_text_font_size = '9pt'
    p_right.legend.location = "top_left"
    p_right.xaxis.axis_label = 'Date'
    p_right.yaxis.axis_label = 'monthly rat sightings'
    p_right.xaxis.axis_label_text_font_size = "14pt"
    p_right.yaxis.axis_label_text_font_size = "14pt"
    p_right.xaxis.axis_label_text_color = '#909090'
    p_right.xaxis.axis_line_color = '#909090'
    p_right.xaxis.major_label_text_color = '#909090'
    p_right.yaxis.axis_label_text_color = '#909090'
    p_right.yaxis.axis_line_color = '#909090'
    p_right.yaxis.major_label_text_color = '#909090'
    p_right.title.text_color = '#909090'
    p_right.legend.label_text_color = '#909090'
    p_right.legend.border_line_color = "#909090"
    p_right.outline_line_color = "#909090"
    p_right.legend.background_fill_color = "black"
       
     
    ###-----------------------------------------------------------------------###
    ###----------------------------CALLBACKS----------------------------------###
    ### This section defines the behavior of the GUI as the user interacts    ###
    ### with the controls.  --------------------------------------------------###
    ###-----------------------------------------------------------------------###

    
    ### Slider callback function       
    callback = CustomJS(args=dict(date_slider = date_slider, zip_select = zip_select, first_source_bait = first_source_bait, original_source_bait = bait_source, bait_indices = indices_bait_source, first_source_sight = first_source_sight, original_source_sight = sight_source, hm_source_original = hm_source_original, hm_source = hm_source, sight_indices = indices_sight_source, timepoints_cds = timepoints_cds, predicted_months_cds = predicted_months_cds), code="""
        var date_slider = new Date(date_slider.value);
        var timepoints_cds = timepoints_cds.data;
        var predicted_months_cds = predicted_months_cds.data;
        var zip_selected = parseFloat(zip_select.value);
        
        var data_bait = first_source_bait.data;
        var whole_data_bait = original_source_bait.data;
        var bait_indices = bait_indices.data;
        
        var data_sight = first_source_sight.data;
        var whole_data_sight = original_source_sight.data;
        var sight_indices = sight_indices.data;
        
        var data_hm = hm_source.data;
        var data_hm_original = hm_source_original.data;
                
        const monthNames = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"];
        var year_month = (date_slider.getUTCFullYear()).toString() +'-'+ monthNames[date_slider.getUTCMonth()];
        console.log(year_month)       
        var g = timepoints_cds['timepoints'].indexOf(year_month)
        
        var test = 0;
        data_hm['start'] = [];
        data_hm['level_0'] = [];
        data_hm['level_1'] = [];
        if(predicted_months_cds['predicted_months'].indexOf(year_month) >= 0 ) {
            for (k = 0; k < 80*80; k++) {
                data_hm['start'].push(data_hm_original['predicted_'+ year_month][k])
                data_hm['level_0'].push(data_hm_original['level_0'][k])
                data_hm['level_1'].push(data_hm_original['level_1'][k])
                test = k;
            }                             
         }
        console.log(data_hm['start'][test]) 
         
        data_bait['LONGITUDE'] = []
        data_bait['LATITUDE'] = []
        data_bait['HOUSE_NUMBER'] = []
        data_bait['STREET_NAME'] = []
        data_bait['ZIP_CODE'] = []
        data_bait['Inspection_Date'] = []
        data_bait['RESULT'] = []
        for (i = bait_indices['from_index'][g]; i < bait_indices['to_index'][g] + 1; i++) {
            if(whole_data_bait['ZIP_CODE'][i] == zip_selected || zip_selected == "all zipcodes" || isNaN(zip_selected)) {
                data_bait['LONGITUDE'].push(whole_data_bait['LONGITUDE'][i])
                data_bait['LATITUDE'].push(whole_data_bait['LATITUDE'][i])
                data_bait['HOUSE_NUMBER'].push(whole_data_bait['HOUSE_NUMBER'][i])
                data_bait['STREET_NAME'].push(whole_data_bait['STREET_NAME'][i])
                data_bait['ZIP_CODE'].push(whole_data_bait['ZIP_CODE'][i])
                data_bait['Inspection_Date'].push(whole_data_bait['Inspection_Date'][i])
                data_bait['RESULT'].push(whole_data_bait['RESULT'][i])
            }
        }
        
        data_sight['LONGITUDE'] = []
        data_sight['LATITUDE'] = []
        data_sight['ADDRESS'] = []
        data_sight['ZIP_CODE'] = []
        data_sight['Sighting_Date'] = []
        for (j = sight_indices['from_index'][g]; j < sight_indices['to_index'][g] + 1; j++) {
            if(whole_data_sight['ZIP_CODE'][j] == zip_selected || zip_selected == "all zipcodes" || isNaN(zip_selected)) {
                data_sight['LONGITUDE'].push(whole_data_sight['LONGITUDE'][j])
                data_sight['LATITUDE'].push(whole_data_sight['LATITUDE'][j])
                data_sight['ADDRESS'].push(whole_data_sight['ADDRESS'][j])
                data_sight['ZIP_CODE'].push(whole_data_sight['ZIP_CODE'][j])
                data_sight['Sighting_Date'].push(whole_data_sight['Sighting_Date'][j])
            }
        }
        
        hm_source.change.emit();
        first_source_sight.change.emit();
        first_source_bait.change.emit();
    """)
    
    ### Zip code select callback function       
    zip_callback = CustomJS(args=dict(zip_select = zip_select, nyc_source = nyc_source, date_slider = date_slider, first_source_bait = first_source_bait, original_source_bait = bait_source, bait_indices = indices_bait_source, first_source_sight = first_source_sight, original_source_sight = sight_source, sight_indices = indices_sight_source, timepoints_cds = timepoints_cds), code="""
        var zip_selected = parseFloat(zip_select.value);
        var date_slider = new Date(date_slider.value);
        var timepoints_cds = timepoints_cds.data;
        
        var nyc_source_data = nyc_source.data;
        var zip_color_selected = "black";
        if (zip_selected == "all zipcodes" || isNaN(zip_selected)) {
            zip_color_selected = "white";
        }
        var zip_color_rest = "white";
        
        var data_bait = first_source_bait.data;
        var whole_data_bait = original_source_bait.data;
        var bait_indices = bait_indices.data;
        
        var data_sight = first_source_sight.data;
        var whole_data_sight = original_source_sight.data;
        var sight_indices = sight_indices.data;
        
        nyc_source_data['colors'] = []
        
        for (i = 0; i <nyc_source_data['ZIPCODE'].length; i++) {
            if (nyc_source_data['ZIPCODE'][i] == zip_selected || zip_selected == "all zipcodes" || isNaN(zip_selected)) {
                nyc_source_data['colors'].push(zip_color_selected);
            } else {
                nyc_source_data['colors'].push(zip_color_rest);
            }                                
        }   
                        
        const monthNames = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"];
        var year_month = (date_slider.getUTCFullYear()).toString() +'-'+ monthNames[date_slider.getUTCMonth()];
        console.log(year_month)
        console.log(zip_selected)
        var g = timepoints_cds['timepoints'].indexOf(year_month)
            
        data_bait['LONGITUDE'] = []
        data_bait['LATITUDE'] = []
        data_bait['HOUSE_NUMBER'] = []
        data_bait['STREET_NAME'] = []
        data_bait['ZIP_CODE'] = []
        data_bait['Inspection_Date'] = []
        data_bait['RESULT'] = []
        for (i = bait_indices['from_index'][g]; i < bait_indices['to_index'][g] + 1; i++) {
            if(whole_data_bait['ZIP_CODE'][i] == zip_selected || zip_selected == "all zipcodes" || isNaN(zip_selected)) {
                data_bait['LONGITUDE'].push(whole_data_bait['LONGITUDE'][i])
                data_bait['LATITUDE'].push(whole_data_bait['LATITUDE'][i])
                data_bait['HOUSE_NUMBER'].push(whole_data_bait['HOUSE_NUMBER'][i])
                data_bait['STREET_NAME'].push(whole_data_bait['STREET_NAME'][i])
                data_bait['ZIP_CODE'].push(whole_data_bait['ZIP_CODE'][i])
                data_bait['Inspection_Date'].push(whole_data_bait['Inspection_Date'][i])
                data_bait['RESULT'].push(whole_data_bait['RESULT'][i])
            }
        }
        
        data_sight['LONGITUDE'] = []
        data_sight['LATITUDE'] = []
        data_sight['ADDRESS'] = []
        data_sight['ZIP_CODE'] = []
        data_sight['Sighting_Date'] = []
        for (j = sight_indices['from_index'][g]; j < sight_indices['to_index'][g] + 1; j++) {
            if(whole_data_sight['ZIP_CODE'][j] == zip_selected || zip_selected == "all zipcodes" || isNaN(zip_selected)) {
                data_sight['LONGITUDE'].push(whole_data_sight['LONGITUDE'][j])
                data_sight['LATITUDE'].push(whole_data_sight['LATITUDE'][j])
                data_sight['ADDRESS'].push(whole_data_sight['ADDRESS'][j])
                data_sight['ZIP_CODE'].push(whole_data_sight['ZIP_CODE'][j])
                data_sight['Sighting_Date'].push(whole_data_sight['Sighting_Date'][j])
            }
        }
        
        first_source_sight.change.emit();
        first_source_bait.change.emit();               
        nyc_source.change.emit();
    """)
    
    zip_select.js_on_change('value', zip_callback)
    date_slider.js_on_change('value', callback)
    
    layout = row(column(row(date_slider, zip_select), p), p_right)
#     layout = gridplot([[p, p_right]])
    
    the_script, the_div = components(layout)
    
    
    ###-----------------------------------------------------------------------###
    ###-----------------------------------------------------------------------###
    ###-----------------------BY ZIPCODES PLOT--------------------------------###
    ###-----------------------------------------------------------------------###
    ###-----------------------------------------------------------------------###
    
    
    colors = ['#f27991', '#f493a7', '#f7aebd', 
         '#fce4e9'] + ['#FFFFFF'] + ['#ddf8fd','#ccf4fd', '#bbf1fc','#aaedfc','#99eafb','#88e6fa', '#77e3fa',
                                     '#66dff9', '#56dcf9']
    mapper = LinearColorMapper(palette=colors, low=by_zipcodes_df.dev.min(), high=by_zipcodes_df.dev.max())
    color_bar = ColorBar(color_mapper=mapper, location=(0, 0), label_standoff=10, 
                         major_label_text_font_size='14pt', major_label_text_color = '#909090',
                        background_fill_color = 'black', scale_alpha = 0.7)

    mp = figure(x_range=(-74.2, -73.7), y_range=(40.53, 40.915), width = 600, height =630,
                tools= 'box_zoom,pan,save,reset', active_drag="box_zoom", background_fill_color = "black",
               min_border_right = 40, min_border_top = 5, min_border_bottom = 5, border_fill_color = "black")
    mp.xgrid.grid_line_color = None
    mp.ygrid.grid_line_color = None
    mp.axis.visible = False
    mp.outline_line_color = "black"
    
    zips = mp.patches('x', 'y', source=nyc_by_zips_source, color='black', line_width=1, 
               fill_color={'field': 'dev', 'transform': mapper}, alpha = 0.7)

    zips_hover = HoverTool(tooltips = """
        <div>
            <div>
                <span style="font-size: 14px; font-weight:bold; color: #000000;">Zip Code: </span> <span style="font-size: 15px; color: #000000">@ZIPCODE</span><br>
                <span style="font-size: 14px; font-weight:bold; color: #000000">Average number of rat sightings per year:</span> <span style="font-size: 15px; color: #000000">@sightings</span><br>
                <span style="font-size: 14px; font-weight:bold; color: #000000;">Average number of interventions per year:</span> <span style="font-size: 15px; color: #000000"> @interventions </span><br>
                <span style="font-size: 14px; font-weight:bold; color: #000000;">Number of interventions above expectation:</span> <span style="font-size: 15px; color: #000000"> @dev </span>
            </div>
        </div>
        """, renderers=[zips])
    mp.add_tools(zips_hover)


    p_zips = figure(title = 'Sightings and interventions by zipcode',tools= 'box_zoom,pan,save,reset', 
                active_drag="box_zoom", background_fill_color = "black",
                   min_border_right = 40, min_border_top = 5, min_border_bottom = 5, border_fill_color = "black")
    points = p_zips.circle(x = 'sightings', y = 'interventions', source = by_zipcodes_source, size=12, 
             fill_color={'field': 'dev', 'transform': mapper}, alpha = 0.7, line_color = 'black')

    p_zips.line(x = 'sightings', y = 'lin_fit', source = by_zipcodes_source, color = 'white')

    p_zips.add_layout(color_bar, 'left')

    points_hover = HoverTool(tooltips = """
        <div>
            <div>
                <span style="font-size: 14px; font-weight:bold; color: #000000;">Zip Code: </span> <span style="font-size: 15px; color: #000000">@ZIP_CODE</span><br>
                <span style="font-size: 14px; font-weight:bold; color: #000000">Average number of rat sightings per year:</span> <span style="font-size: 15px; color: #000000">@sightings</span><br>
                <span style="font-size: 14px; font-weight:bold; color: #000000;">Average number of interventions per year:</span> <span style="font-size: 15px; color: #000000"> @interventions </span><br>
                <span style="font-size: 14px; font-weight:bold; color: #000000;">Number of interventions above expectation:</span> <span style="font-size: 15px; color: #000000"> @dev </span>
            </div>
        </div>
        """, renderers=[points])
    p_zips.add_tools(points_hover)
    p_zips.xaxis.major_label_text_font_size = "14pt"
    p_zips.yaxis.major_label_text_font_size = "14pt"
    p_zips.title.text_font_size = '16pt'
    p_zips.xaxis.axis_label = 'average number of rat sightings per year'
    p_zips.yaxis.axis_label = 'average number of interventions per year'
    p_zips.xaxis.axis_label_text_font_size = "14pt"
    p_zips.yaxis.axis_label_text_font_size = "14pt"
    p_zips.xaxis.axis_label_text_color = '#909090'
    p_zips.xaxis.axis_line_color = '#909090'
    p_zips.xaxis.major_label_text_color = '#909090'
    p_zips.yaxis.axis_label_text_color = '#909090'
    p_zips.yaxis.axis_line_color = '#909090'
    p_zips.yaxis.major_label_text_color = '#909090'
    p_zips.title.text_color = '#909090'

    layout_zips = row(mp,p_zips)
    
    the_script_zips, the_div_zips = components(layout_zips)

       
    ###-----------------------------------------------------------------------###
    ###-----------------------------------------------------------------------###
    ###--------------------------HEATMAPS PLOT--------------------------------###
    ###-------------------------  BY ZIPCODE----------------------------------###
    ###-----------------------------------------------------------------------###
  

    colors_hm = ['#fdf1f4', '#fce4e9', '#fbd6de', '#f9c9d3', '#f8bcc8', 
              '#f7aebd', '#f5a1b2','#f493a7', '#f3869c', '#f27991'] 
    mapper_hm = LinearColorMapper(palette=colors_hm, low=0, high=50)
    hm_color_bar = ColorBar(color_mapper=mapper_hm, location=(0, 0), label_standoff=10, 
                         major_label_text_font_size='14pt', major_label_text_color = '#909090',
                           background_fill_color = 'black', scale_alpha = 0.7)

    heatmap = figure(x_range=(-74.2, -73.7), y_range=(40.53, 40.915), width = 500, height =500,
                tools= 'box_zoom,pan,save,reset', active_drag="box_zoom", background_fill_color = "black",
                     min_border_top = 5, min_border_bottom = 5, border_fill_color = "black",
                    toolbar_location="left")
    heatmap.xgrid.grid_line_color = None
    heatmap.ygrid.grid_line_color = None
    heatmap.axis.visible = False
    heatmap.outline_line_color = "black"

    zips_hm = heatmap.patches('x', 'y', source=zip_hm_first, color='black', line_width=1, 
               fill_color={'field': 'sightings', 'transform': mapper_hm}, alpha = 0.7)

    zips_hm_hover = HoverTool(tooltips = """
        <div>
            <div>
                <span style="font-size: 14px; font-weight:bold; color: #000000;">Zip Code: </span> <span style="font-size: 15px; color: #000000">@ZIPCODE</span><br>
                <span style="font-size: 14px; font-weight:bold; color: #000000">Number of sightings this month:</span> <span style="font-size: 15px; color: #000000">@sightings</span><br>
            </div>
        </div>
        """, renderers=[zips_hm])
    heatmap.add_tools(zips_hm_hover)

    dummy = figure(height=500, width=150, toolbar_location=None, min_border=0, outline_line_color=None,
                  background_fill_color = "black",
                     min_border_top = 5, min_border_bottom = 5, border_fill_color = "black")
    dummy.add_layout(hm_color_bar, 'right')

    ### Add slider
    date_slider_hm = DateSlider(title="Date", start=dt.date(2010, 1, 1), end=dt.date(2018, 4, 1),value=dt.date(2014, 7, 1), step=1, format = "%B %Y")

    ### Slider callback function       
    hm_callback = CustomJS(args=dict(date_slider = date_slider_hm,
                                  zip_hm_first = zip_hm_first, zip_hm_original = zip_hm_original), 
                        code="""
        var date_slider = new Date(date_slider.value);

        var data_hm = zip_hm_first.data;
        var data_hm_original = zip_hm_original.data;

        const monthNames = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"];
        var year_month = (date_slider.getUTCFullYear()).toString() +'-'+ monthNames[date_slider.getUTCMonth()];
        console.log(year_month)       

        var test = 0;
        data_hm['sightings'] = [];
        for (k = 0; k < 263; k++) {
            data_hm['sightings'].push(data_hm_original[year_month][k])
        }                             

        zip_hm_first.change.emit();

    """)

    date_slider_hm.js_on_change('value', hm_callback)

    layout_hm = column(date_slider_hm,row(heatmap, dummy))
    
    the_script_hm, the_div_hm = components(layout_hm)


    
    return render_template('myindex-pitch-night.html', div = the_div, script=the_script, 
                           the_script_zips = the_script_zips, the_div_zips = the_div_zips,
                          the_script_hm = the_script_hm, the_div_hm = the_div_hm)   


@app.route('/index')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')