#!/usr/bin/env python
# ****************************************************************************
# nc2shp.py
#
# DESCRIPTION:
# Create shapefile from (2D) netCDF data contours. The contours are created
# with matplotlib, and the corresponding polylines are then written to a 
# shapefile. This routine also creates a figure with one of the contour lines
# filled.
# See argument parser for detailed description of input arguments.
# 
# EXAMPLES:
# python nc2shp.py -i 'https://opendap.nccs.nasa.gov/dods/gmao/geos-cf/assim/chm_tavg_1hr_g1440x721_v1' -y 2020 -m 1 -d 1 -v 'pm25_rh35_gcc' -c 10.0 25.0 -o 'pm25_%Y%m%d.shp' -ff 'pm25_plumes_%Y%m%d.png' -fc 25.0 -ft 'Surface PM2.5 >= 25$\mu$gm$^{-3}$ (%Y-%m-%d)'
# python nc2shp.py -i 'https://opendap.nccs.nasa.gov/dods/gmao/geos-cf/assim/xgc_tavg_1hr_g1440x721_x1' -y 2020 -m 1 -d 1 -v 'aod550_dust' 'aod550_sala' 'aod550_salc' 'aod550_oc' 'aod550_bc' 'aod550_sulfate' -c 0.25 0.5 -o 'aod_gcc__%Y%m%d.shp' -ff 'aod_plumes_gcc_%Y%m%d.png' -fc 0.25 -ft 'AOD > 0.25 (%Y-%m-%d)' -cl 180 -ex -120 240 -80 80

#
# HISTORY:
# christoph.a.keller@nasa.gov - 01/05/2020 - Initial version
# ****************************************************************************

import datetime as dt
from shapely import geometry
import matplotlib.pyplot as plt
from matplotlib import cm
import numpy as np
import fiona
import os,json
from descartes.patch import PolygonPatch
import xarray as xr
import shapefile as shp
import cartopy.crs as ccrs
import cartopy.feature
import argparse
import pandas as pd
import logging


def read_nc(ifile,start,end,vars,scal=1.0,func="mean"):
    '''Read netCDF file and return 2D array and the mean time stamp'''

    log = logging.getLogger(__name__)
    ifile_parsed = start.strftime(ifile)
    log.info('Reading {}'.format(ifile_parsed))
    if '*' in ifile:
        ds = xr.open_mfdataset(ifile_parsed)
    else:
        ds = xr.open_dataset(ifile_parsed)

    if len(ds.time)>1:
        ds = ds.sel(time=slice(start,end))

    if type(vars)==type(""):
        vars = [vars]
    for c,v in enumerate(vars):
        if c==0:
            arrs = ds[v]
        else:
            arrs = arrs + ds[v]

    times = arrs.time.values
    m = times.min()
    meantime = pd.to_datetime(str((m + (times - m).mean())))

    if func=="mean":
        arr = arrs.mean(dim='time')
    if func=="max":
        arr = arrs.max(dim='time')
    if func=="min":
        arr = arrs.min(dim='time')

    if 'lev' in arr.dims:
        arr = arr.squeeze('lev')

    if scal != 1.0:
        arr = arr*scal

    ds.close()
    return arr, meantime


def get_contours(arr,contours,contour_figname):
    '''Draw contours of a 2D array and return corresponding object'''

    log = logging.getLogger(__name__)
    plt.figure(figsize=[5,5])
    cs = plt.contour(arr.lon.values,arr.lat.values,arr.values,contours)
    if contour_figname is not None:
        plt.savefig(contour_figname)
        log.info('Original figure written to {}'.format(contour_figname))
    plt.close()
    return cs    


def write_shapefile(cs,propname,shapefile):
    '''Write matplotlib contours to shapefile'''

    log = logging.getLogger(__name__)
    levels = dict(zip(cs.collections, cs.levels))
    polylist = []
    for col in cs.collections:
        z = levels[col]
        for path in col.get_paths():
            v = path.vertices
            lons = v[:,0]
            lats = v[:,1]
            poly = geometry.Polygon([(i[0], i[1]) for i in zip(lons,lats)])
            polylist.append({'poly':poly,'props':{propname:z}})
    
    # write to shapefile
    schema = {'geometry': 'Polygon','properties': {propname: 'float'}}
    with fiona.collection(shapefile, "w", "ESRI Shapefile", schema) as output:
        for p in polylist:
            output.write({'properties': p['props'],
                'geometry': geometry.mapping(p['poly'])})
    log.info('Shapefile written to file {}'.format(shapefile))
    return 

 
def read_shapefile_and_plot_filled_contour(shapefile,contour,ofile,title,central_longitude=0,extent=[-180,180,-80,80]):
    '''read shapefile and make plot with filled contour for the given contour level''' 

    if ofile is None:
        return
    log = logging.getLogger(__name__)
    if shapefile is None:
        log.error('Cannot read shapefile - not defined!')
        return
    sf = shp.Reader(shapefile)
    proj = ccrs.PlateCarree(central_longitude=central_longitude)
    proj_box = ccrs.PlateCarree()
    ax = plt.axes(projection=proj)
    ax.set_extent(extent, proj_box)
    _ = ax.add_feature(cartopy.feature.LAND)
    _ = ax.add_feature(cartopy.feature.OCEAN)
    _ = ax.add_feature(cartopy.feature.COASTLINE, edgecolor="black")
    for shape in sf.shapeRecords():
        if shape.record[0]==contour:
            x = [i[0] for i in shape.shape.points[:]]
            y = [i[1] for i in shape.shape.points[:]]
            _ = ax.fill(x,y,transform=proj_box,color='red')
    plt.title(title)
    plt.savefig(ofile)
    log.info('Test figure written to {}'.format(ofile))
    plt.close()
    return


def get_analysis_date(year,month,day,time_window):
    '''Return the analysis date, parsed from the input arguments.'''
    today = dt.datetime.today() - dt.timedelta(days=1)
    year = year if year is not None else today.year   
    month = month if month is not None else today.month   
    day = day if day is not None else today.day   
    hour = 0
    minute = 0
    start = dt.datetime(year,month,day,hour,minute,0)
    end = start + dt.timedelta(hours=time_window)
    return start,end


def main(args):
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)
#---Read netCDF file
    start,end = get_analysis_date(args.year,args.month,args.day,args.time_window)
    arr, meantime = read_nc(args.ifile,start,end,args.ncvars,args.ncscal,args.func)
#---Get contours, eventually write to shapefile
    figname = meantime.strftime(args.contour_figname) if args.contour_figname is not None else None
    cs = get_contours(arr,args.contours,figname)
#---Write contours to shapefile
    shapefile = meantime.strftime(args.shapefile) if args.shapefile is not None else None
    write_shapefile(cs,args.propname,shapefile)
#---Create figure with one filled contour, read from the shapefile
    fillfig_contour = args.fillfig_contour if args.fillfig_contour is not None else args.contours[0]
    read_shapefile_and_plot_filled_contour(
        shapefile=shapefile,
        contour=fillfig_contour,
        ofile=meantime.strftime(args.fillfig_name),
        title=meantime.strftime(args.fillfig_title),
        central_longitude=args.central_longitude,
        extent=args.extent)
    return


def parse_args(args=None):
    '''
    Function argument parser

    Arguments
    ----------
    ifile : str
        NetCDF file to be read. Can contain multiple time stamps in the same
        file, or multiple files to be read at once (use asterisk in the file
        name in the latter case). Also accepts OPeNDAP address.
    year : int
        Start year for data to be analyzed. Will use yesterday if set to None.
    month : int
        Start month for data to be analyzed. Will use yesterday if set to None.
    day : int
        Start day for data to be analyzed. Will use yesterday if set to None.
    time-window : int
        Time window of data to be analyzed. In hours. Defaults to 24 hours.
    ncvars : str
        Variables on netCDF file to use. Can be more than one variable, in 
        which case the variables are added together.
    ncscal : float
        Scale factor to be applied to netCDF data (after aggregation).
    func : str
        Temporal aggregation method if data has more than one time stamp. 
        Can be one of 'mean', 'min', 'max'.
    contours : float
        Contour levels to use. Can be more than one.
    shapefile : str
        File name to write shapefile to.
    propname : str
        Property name to use in shapefile.
    contour-figname: str
        If not None, create a contour figure from the originally read netCDF
        data. This is useful to make sure that the shapefile conversion yields
        the expected result.
    fillfig-name : str
        Name of file with filled contour plot.
    fillfig-contour : float
        Contour level to use for filled contour plot. If set to None, uses the first value of contours.
    fillfig-title : str
        Title to use in filled contour plot. Accepts datetime tokens to be parsed by strftime.
    central-longitude : int
        Central longitude used in filled contour figure.
    extent : int
        Geographical extent of filled contour figure. 
    '''

    p = argparse.ArgumentParser(description='Undef certain variables')
    p.add_argument('-i','--ifile',type=str,help='input netCDF file',default='https://opendap.nccs.nasa.gov/dods/gmao/geos-cf/assim/chm_tavg_1hr_g1440x721_v1')
    p.add_argument('-y','--year',type=int,help='data start year',default=None)
    p.add_argument('-m','--month',type=int,help='data start month',default=None)
    p.add_argument('-d','--day',type=int,help='data start day',default=None)
    p.add_argument('-t','--time-window',type=int,help='data time window, in hours',default=24)
    p.add_argument('-v','--ncvars',type=str,nargs='+',help='netCDF variables to use', default=['pm25_rh35_gcc'])
    p.add_argument('-s','--ncscal',type=float,help='scale factor applied to netCDF data', default=1.0)
    p.add_argument('-f','--func',type=str,help='averaging function to apply to input data',default='mean')
    p.add_argument('-c','--contours',type=float,nargs='+',help='list of contour lines',default=[10.0, 25.0])
    p.add_argument('-o','--shapefile',type=str,help='output shapefile',default='pm25_%Y%m%d.shp')
    p.add_argument('-p','--propname',type=str,help='shapefile property name',default='pm25')
    p.add_argument('-cf','--contour-figname',type=str,help='file name of contour figure',default=None)
    p.add_argument('-ff','--fillfig-name',type=str,help='file name of filled contour figure',default='pm25_%Y%m%d.png')
    p.add_argument('-fc','--fillfig-contour',type=float,help='contour to use for filled contour figure',default=25.0)
    p.add_argument('-ft','--fillfig-title',type=str,help='title for filled contour figure',default='Surface PM2.5 >= 25$\,\mu$gm$^{-3}$ (%Y-%m-%d)')
    p.add_argument('-cl','--central-longitude',type=int,help='central longitude used in filled contour figure',default=0)
    p.add_argument('-ex','--extent',nargs=4,type=int,help='extent of filled contour figure',default=[-180, 180, -90, 90])
    return p.parse_args(args)


if __name__ == "__main__":
    main(parse_args())
