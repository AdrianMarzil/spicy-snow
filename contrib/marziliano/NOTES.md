<hr>
<b> NOTES
<br>
<br>From README file ... </b>
<br>
<br>Function to actually get data, run processing, returns xarray dataset w/ daily time dimension
<br> s1_sd = get_s1_snow_depth(area, dates, work_dir = './idaho_retrieval/)
<br>
<br> Should 'get_s1_snow_depth' be 'retrieve_snow_depth'?
<br>
<br><b>For future ... </b>
<br>
<br> 1. Ability to download multiple years between snow season dates only?
<br>
<br> 2. If fcf or ims already downloaded, can we use that file instead of redownloading?
<br> Skipped for fcf once with exact same search dates/area
<br> 
<br> 3. If error occured in the middle of S1 download, can we start over based on what was completed?
<br>
<br> 4. More instructions about dates e.g. (End Date, Beginning Date); Has to include at least 2 different retrievals (6-12 date interval minimum) for Snow Index(?)
<br> e.g., dates = get_input_dates("2022-05-31", "2021-11-01") <br>
<hr>