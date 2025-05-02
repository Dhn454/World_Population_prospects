import redis 
import os
import logging 
from hotqueue import HotQueue 
from jobs import update_job_status, get_job_by_id, string_to_bool
from api import get_year 
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np
from collections import defaultdict
import json 
from sklearn.linear_model import LinearRegression

_redis_port=6379 
_redis_host = os.environ.get("REDIS_HOST") # AI used to understand environment function 

rd = redis.Redis(host=_redis_host, port=_redis_port, db=0)
q = HotQueue("queue", host=_redis_host, port=_redis_port, db=1) 
resdb = redis.Redis(host=_redis_host, port=_redis_port, db=3) 

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
numeric_level = getattr(logging, log_level, logging.INFO)

logging.basicConfig(
    level=numeric_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
logger.info("Logging level set to %s", log_level)

def manipulate_data(job_data):
    """This funciton converts the list of dictionaries into a single dictionary of dictionaries
    

    Args:
        data (_type_): _description_

    """
    start = job_data.get('start')
    end = job_data.get('end') 
    regions = job_data.get('location')
    raw_data = get_year(f'{start}-{end}', regions)
    # raw_data = raw_data.json() 
    new_data = defaultdict(lambda: defaultdict(list))
    logging.debug(f"Type of raw_data: {type(raw_data)}")
    logging.debug(f'Parameters: {start}-{end}, {regions}')
    for entry in raw_data:
        if not entry["Time"]:
            continue
        year = entry["Time"]
        if not entry["Location"]:
            continue
        location = entry["Location"]
        new_data[year][location].append(entry)
    return {year: dict(locations) for year, locations in new_data.items()}

def plot_data(new_data, jobid, start_year, end_year, plot_type='line', Location='World', query1='TPopulationJan1', query2=None, animate=False):
    """
    """
    Location = Location or 'World'
    plot_type = plot_type or 'line'
    animate = animate or False
    query1 = query1 or 'TPopulationJan1'

    Time_range = [str(year) for year in range(start_year, end_year + 1)]
    logging.debug(f'Time_range is of type: {type(Time_range)}')
    logging.debug(f'Time_range has data: {Time_range}')
    years_int = [int(y) for y in Time_range]
    num_locations = len(Location) if Location else 0
    
    if Location and len(Location) > 1: Location.sort()
    logging.debug(f'Location is of type: {type(Location)}')
    logging.debug(f'Location has data: {Location}')
    if plot_type == "line":
        plt.figure(figsize=(10, 6))
        for loc in Location:
            values = []
            logging.debug("starting for loop for locations")
            for year in Time_range:
                try:
                    entry = new_data[year][loc][0]
                    val = float(entry[query1])
                except (KeyError, IndexError, ValueError):
                    val = None
                values.append(val)
                
            if any(val is not None for val in values):
                plt.plot(years_int, values, label=loc)
        
        plt.xlabel("Year")
        plt.ylabel(f'{query1}')
        plt.title(f"{query1} vs Year by Location")
        plt.legend(loc='upper left', bbox_to_anchor=(1.02, 1), borderaxespad=0)
        plt.grid(True)
        plt.savefig(f'{jobid}.png', bbox_inches='tight')
    
    elif plot_type == "bar":
        val_over_time = []
        for year in Time_range:
            year_values = []
            for loc in Location:
                try:
                    val = float(new_data[year][loc][0][query1])
                except (KeyError, IndexError, ValueError):
                    val = None
                year_values.append(val)
            val_over_time.append(year_values)
                    
        cmap = plt.colormaps.get_cmap('Pastel1').resampled(num_locations)
        colors = [mcolors.to_hex(cmap(i)) for i in range(num_locations)]
                
        if animate ==True:
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.bar(Location, val_over_time[0], color=colors)
            ax.set_ylim(0, max(max(row) for row in val_over_time) * 1.1)
            ax.set_ylabel(f"{query1}")
            title = ax.set_title(f"{query1} in {years_int[0]}")
            texts = [ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f"{(bar.get_height()):,}", 
                 ha='center', va='bottom', fontsize=9) for bar in bars]
            
            def update(frame):
                year = years_int[frame]
                title.set_text(f"{query1} in {year}")
                for bar, height, text in zip(bars, val_over_time[frame], texts):
                    bar.set_height(height)
                    text.set_y(height)
                    text.set_text(f"{(height):,}")
                    
            ani = animation.FuncAnimation(fig, update, frames=len(years_int), repeat=True, interval=1000)
            ani.save(f'{jobid}.gif', writer='pillow', fps=3)
            
            
        
        elif animate == False:
            for i, year in enumerate(Time_range):
                fig, ax = plt.subplots(figsize=(10, 6))
                bars = ax.bar(Location, val_over_time[i], color=colors)
                ax.set_ylim(0, max(max(row) for row in val_over_time) * 1.1)
                ax.set_ylabel(f"{query1}")
                title = ax.set_title(f"{query1} in {year}")
                
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2, height, f"{(height):,}", 
                            ha='center', va='bottom', fontsize=9)
                plt.tight_layout()
                plt.savefig(f'{jobid}_{year}.png', bbox_inches='tight')
                plt.close(fig)
            
            
    elif plot_type == "scatter":
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.subplots_adjust(right=0.75)
        sc = ax.scatter([], [], alpha=1)
        reg_line, = ax.plot([], [], color='red', lw=2, label='Regression Line')
        title = ax.set_title("")
        xlabel = ax.set_xlabel(f"{query1}")
        ylabel = ax.set_ylabel(f"{query2}")
        
        x_vals_all, y_vals_all = [], []
        for year in Time_range:
            for loc in Location:
                try:
                    entry = new_data[year][loc][0]
                    x_vals_all.append(float(entry[query1]))
                    y_vals_all.append(float(entry[query2]))
                except (KeyError, IndexError, ValueError):
                    continue
        x_min, x_max = min(x_vals_all), max(x_vals_all)
        y_min, y_max = min(y_vals_all), max(y_vals_all)
        x_pad = (x_max - x_min) * 0.1
        y_pad = (y_max - y_min) * 0.1
        x_lim = (x_min - x_pad, x_max + x_pad)
        y_lim = (y_min - y_pad, y_max + y_pad)
        
        unique_locations = sorted({loc for year in Time_range for loc in new_data[year].keys()})
        num_locations = len(unique_locations)
        cmap = plt.colormaps.get_cmap('plasma').resampled(num_locations)
        loc_to_color = {loc: cmap(i) for i, loc in enumerate(unique_locations)}
        
        def plot_for_year(year):
            ax.clear()
            ax.set_xlabel(f"{query1}")
            ax.set_ylabel(f"{query2}")
            ax.set_title(f"{query1} vs {query2} in {year}")
            ax.grid(True)
            ax.set_xlim(x_lim)
            ax.set_ylim(y_lim)
            
            x_vals, y_vals, labels = [], [], []
            for loc in Location:
                try:
                    entry = new_data[year][loc][0]
                    x = float(entry[query1])
                    y = float(entry[query2])
                    x_vals.append(x)
                    y_vals.append(y)
                    labels.append(loc)
                except (KeyError, IndexError, ValueError):
                    continue
                
            colors = [loc_to_color[loc] for loc in labels]
            ax.scatter(x_vals, y_vals, c=colors, alpha=1)
        
            if len(x_vals) > 1:
                X = np.array(x_vals).reshape(-1, 1)
                y = np.array(y_vals)
                model = LinearRegression().fit(X, y)
                r_squared = model.score(X, y)
                x_fit = np.linspace(x_lim[0], x_lim[1], 100).reshape(-1, 1)
                y_fit = model.predict(x_fit)
                reg_label = f"Regression Line (R²={r_squared:.2f})"
                ax.plot(x_fit, y_fit, color='red', lw=2, label=reg_label)
                location_handles = [plt.Line2D([0], [0], marker='o', linestyle='', color=loc_to_color[loc],
                                               label=loc, markersize=7) for loc in unique_locations]

                regression_handle = plt.Line2D([0], [0], color='red', lw=2, label=reg_label)
                all_handles = [regression_handle] + location_handles
                legend = ax.legend(handles=all_handles, loc='upper right', bbox_to_anchor=(1.4, 1), borderaxespad=0)
                legend.get_frame().set_facecolor('none')
                legend.get_frame().set_edgecolor('none')
        
        if animate == True:
            def update(frame):
                year = Time_range[frame]
                plot_for_year(year)
                
            ani = animation.FuncAnimation(fig, update, frames=len(Time_range), repeat=True, interval=1000)
            ani.save(f'{jobid}.gif', writer='pillow', fps=3)
            
        else:
            for year in Time_range:
                fig, ax = plt.subplots(figsize=(10, 6))  # Move inside loop
                def plot_for_year_dynamic(ax, year):
                    ax.set_xlabel(f"{query1}")
                    ax.set_ylabel(f"{query2}")
                    ax.set_title(f"{query1} vs {query2} in {year}")
                    ax.grid(True)
                    ax.set_xlim(x_lim)
                    ax.set_ylim(y_lim)
        
                    x_vals, y_vals, labels = [], [], []
                    for loc in Location:
                        try:
                            entry = new_data[year][loc][0]
                            x = float(entry[query1])
                            y = float(entry[query2])
                            x_vals.append(x)
                            y_vals.append(y)
                            labels.append(loc)
                        except (KeyError, IndexError, ValueError):
                            continue
                        
                    colors = [loc_to_color[loc] for loc in labels]
                    ax.scatter(x_vals, y_vals, c=colors, alpha=1)
        
                    if len(x_vals) > 1:
                        X = np.array(x_vals).reshape(-1, 1)
                        y_arr = np.array(y_vals)
                        model = LinearRegression().fit(X, y_arr)
                        r_squared = model.score(X, y_arr)
                        x_fit = np.linspace(x_lim[0], x_lim[1], 100).reshape(-1, 1)
                        y_fit = model.predict(x_fit)
                        reg_label = f"Regression Line (R²={r_squared:.2f})"
                        ax.plot(x_fit, y_fit, color='red', lw=2, label=reg_label)
        
                        location_handles = [plt.Line2D([0], [0], marker='o', linestyle='', color=loc_to_color[loc],
                                                       label=loc, markersize=7) for loc in unique_locations]
                        regression_handle = plt.Line2D([0], [0], color='red', lw=2, label=reg_label)
                        all_handles = [regression_handle] + location_handles
                        legend = ax.legend(handles=all_handles, loc='upper right', bbox_to_anchor=(1.3, 1), borderaxespad=0)
                        legend.get_frame().set_facecolor('none')
                        legend.get_frame().set_edgecolor('none')
                        for text in legend.get_texts():
                            text.set_ha("right")
        
                plot_for_year_dynamic(ax, year)
                plt.savefig(f'{jobid}_{year}.png', bbox_inches='tight')
                plt.close(fig)

            
    else:
        raise ValueError("Invalid plot type. Choose 'line', 'bar', or 'scatter'.")
    
    logging.debug("starting to save results")
    logging.debug(f'animate option is {animate}')
    if animate == False:
        if plot_type == "bar" or plot_type == "scatter":
            for year in Time_range:
                filename = f"{jobid}_{year}.png"
                try:
                    with open(filename, 'rb') as f:
                        image_data = f.read()
                    logging.debug("successfully opened image")
                    resdb.hset(jobid, f'image_{year}', image_data)
                    logging.debug(f"Saved image_{year} to Redis for job {jobid}")
                    resdb.hset(jobid,"data",json.dumps(new_data))
                except FileNotFoundError:
                    logging.error(f"File {filename} not found.")
        elif plot_type == "line":
            filename = f"{jobid}.png"
            try:
                with open(filename, 'rb') as f:
                    image_data = f.read()
                logging.debug("successfully opened image")
                resdb.hset(jobid, "image", image_data)
                resdb.hset(jobid,"data",json.dumps(new_data))
            except FileNotFoundError:
                logging.error(f"File {filename} not found.")
            
    elif animate == True:
        with open(f'{jobid}.gif', 'rb') as f:
            gif_data = f.read()
        resdb.hset(jobid, "gif", gif_data)
        logging.debug("successfully saved gif to Redis")
        

@q.worker
def update(jobid: str): 

    logging.info(f"Started processing job: {jobid}")
    try:
        update_job_status(jobid, 'in progress')

        # WORK STARTING  
        job_dict = get_job_by_id(jobid)
        logging.debug(f'job_dict is of type: {type(job_dict)}')
        logging.debug(f'job_dict has data: {job_dict}')
        if "error" in job_dict:
            raise Exception(f"Error retrieving job {jobid}: {job_dict['error']}")
        
        new_data = manipulate_data(job_dict) 
        logging.debug(f'new_data is of type: {type(new_data)}')
        logging.debug(f'new_data dictionaries: {new_data.keys()}')

        region_names = job_dict.get("location")
        regions = region_names.split(",") if region_names else []

        plot_data(new_data, jobid, int(job_dict["start"]), int(job_dict["end"]), job_dict["plot_type"], 
                  regions, job_dict.get("query1"), job_dict.get("query2"), string_to_bool(job_dict.get("animate")))

        update_job_status(jobid, 'complete') 
    except Exception as e:
        update_job_status(jobid, 'error')  # If something goes wrong, mark job as error.
        logging.error(f"Error processing job {jobid}: {e}") 

update() 
