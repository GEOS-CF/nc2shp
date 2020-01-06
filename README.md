# nc2shp
Function to create a shapefile from netCDF data contours. The contours are created using matplotlib, and the corresponding polylines are then written to a shapefile. This routine also creates a figure with one of the contour lines filled. See argument parser for detailed description of input arguments.

# Examples

1. Create a shapefile containing the PM2.5 data contours for 10 ug/m3 and 25 ug/m3, respectively, as simulated by GEOS-CF for January 1, 2020. Also make a figure showing the filled 25 ug/m3 data contours:

  python nc2shp.py -i 'https://opendap.nccs.nasa.gov/dods/gmao/geos-cf/assim/chm_tavg_1hr_g1440x721_v1' -y 2020 -m 1 -d 1 -v 'pm25_rh35_gcc' -c 10.0 25.0 -o 'shp/pm25_%Y%m%d.shp' -ff 'pm25_plumes_%Y%m%d.png' -fc 25.0 -ft 'Surface PM2.5 >= 25$\mu$gm$^{-3}$ (%Y-%m-%d)'

1. Create a shapefile containing the total aerosol optical depth (AOD) at 550nm contours for AOD levels 0.25 and 0.5, respectively, as simulated by GEOS-CF for January 1, 2020. Calculate total AOD from fields aod550_dust, aod550_sala, aod550_salc, aod550_oc, aod550_bc, and aod550_sulfate. Also make a figure showing the filled 0.25 data contours, centered at 180 degrees East and extending from 0 - 360 degrees East and -80 - 80 degrees North:

  python nc2shp.py -i 'https://opendap.nccs.nasa.gov/dods/gmao/geos-cf/assim/xgc_tavg_1hr_g1440x721_x1' -y 2020 -m 1 -d 1 -v 'aod550_dust' 'aod550_sala' 'aod550_salc' 'aod550_oc' 'aod550_bc' 'aod550_sulfate' -c 0.25 0.5 -o 'aod_gcc__%Y%m%d.shp' -ff 'zod_plumes_gcc_%Y%m%d.png' -fc 0.25 -ft 'AOD > 0.25 (%Y-%m-%d)' -cl 180 -ex -120 240 -80 80
