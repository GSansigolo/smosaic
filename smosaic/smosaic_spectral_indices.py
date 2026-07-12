import os
import re
import rasterio
import subprocess
import numpy as np
from rasterio.enums import Resampling
from rasterio.windows import Window

def fix_negatives(input_file):
    temp_file = input_file.replace('.tif', '_temp.tif')
    
    with rasterio.open(input_file) as src:
        data = src.read()
        meta = src.meta.copy()
        meta.update({'dtype': 'int16', 'nodata': 0})
        
        mask = data < 0
        data[mask] = 0
        
        meta.update({
            'dtype': 'int16',
            'nodata': 0
        })
        
        with rasterio.open(temp_file, 'w', **meta) as dst:
            dst.write(data)
    
    os.remove(input_file)
    os.rename(temp_file, input_file)
    
def ndvi_calc(nir, red, file_name, compress='LZW'):
    
    with rasterio.open(red) as red_src, \
        rasterio.open(nir) as nir_src:
        
        meta = red_src.meta.copy()
        meta.update({'dtype': 'int16', 'nodata': -9999})
        
        with rasterio.open(file_name, 'w', **meta) as dst:
            
            for ji, window in red_src.block_windows(1):
            
                red = red_src.read(1, window=window, masked=True).astype(np.float32)
                nir = nir_src.read(1, window=window, masked=True).astype(np.float32)
                
                ndvi = (nir - red) / (nir + red)

                ndvi_int16 = (ndvi * 10000).astype(np.int16)

                dst.write(ndvi_int16, 1, window=window)

        print(f"Raster saved to: {str(file_name)}")

def evi_calc(nir, red, blue, file_name, compress='LZW'):
    
    with rasterio.open(red) as red_src, \
        rasterio.open(nir) as nir_src, \
        rasterio.open(blue) as blue_src:
        
        meta = red_src.meta.copy()
        meta.update({'dtype': 'int16', 'nodata': -9999})
        
        with rasterio.open(file_name, 'w', **meta) as dst:
            
            for ji, window in red_src.block_windows(1):
            
                red = red_src.read(1, window=window, masked=True).astype(np.float32)
                nir = nir_src.read(1, window=window, masked=True).astype(np.float32)
                blue = blue_src.read(1, window=window, masked=True).astype(np.float32)
                
                evi =  2.5 * ((nir-red)/((nir+6*red-7.5*blue)+1))

                evi_int16 = (evi * 10000).astype(np.int16)

                dst.write(evi_int16, 1, window=window)
                
        print(f"Raster saved to: {str(file_name)}")

def evi2_calc(nir, red, file_name, compress='LZW'):
    
    with rasterio.open(red) as red_src, \
        rasterio.open(nir) as nir_src:
        
        meta = red_src.meta.copy()
        meta.update({'dtype': 'int16', 'nodata': -9999})
        
        with rasterio.open(file_name, 'w', **meta) as dst:
            
            for ji, window in red_src.block_windows(1):
            
                red = red_src.read(1, window=window, masked=True).astype(np.float32)
                nir = nir_src.read(1, window=window, masked=True).astype(np.float32)
                
                evi2 = 2.5 * ((nir - red) / (nir + red + 1))
                      
                evi2_int16 = (evi2 * 10000).astype(np.int16)

                dst.write(evi2_int16, 1, window=window)
                
        print(f"Raster saved to: {str(file_name)}")

def savi_calc(nir, red, file_name, compress='LZW'):
    
    with rasterio.open(red) as red_src, \
        rasterio.open(nir) as nir_src:
        
        meta = red_src.meta.copy()
        meta.update({'dtype': 'int16', 'nodata': -9999})
        
        with rasterio.open(file_name, 'w', **meta) as dst:
            
            for ji, window in red_src.block_windows(1):
            
                red = red_src.read(1, window=window, masked=True).astype(np.float32)
                nir = nir_src.read(1, window=window, masked=True).astype(np.float32)
                
                savi = ((1+0.5)*(nir - red))/(nir + red + 0.5)

                savi_int16 = (savi * 10000).astype(np.int16)

                dst.write(savi_int16, 1, window=window)
                
        print(f"Raster saved to: {str(file_name)}")

def ndbi_calc(swir_path, nir_path, file_name, compress='LZW'):
    
    with rasterio.open(nir_path) as nir_src, \
         rasterio.open(swir_path) as swir_src:
        
        meta = nir_src.meta.copy()
        meta.update({
            'dtype': 'int16', 
            'nodata': -9999,
            'count': 1,
            'compress': compress
        })
        
        with rasterio.open(file_name, 'w', **meta) as dst:
            
            for ji, nir_window in nir_src.block_windows(1):
            
                scale = 0.5
                swir_window = Window(
                    col_off=int(nir_window.col_off * scale),
                    row_off=int(nir_window.row_off * scale),
                    width=int(nir_window.width * scale),
                    height=int(nir_window.height * scale)
                )
                
                nir = nir_src.read(1, window=nir_window, masked=True).astype(np.float32)
                
                swir = swir_src.read(
                    1, 
                    window=swir_window, 
                    out_shape=nir.shape, 
                    resampling=Resampling.bilinear,
                    masked=True
                ).astype(np.float32)
                
                with np.errstate(divide='ignore', invalid='ignore'):
                    ndbi = (swir - nir) / (swir + nir)

                nodata_mask = np.ma.getmask(ndbi)
                ndbi_int16 = (ndbi * 10000).astype(np.int16)
                ndbi_int16[nodata_mask] = meta['nodata']

                dst.write(ndbi_int16, 1, window=nir_window)

        print(f"Raster saved to: {str(file_name)}")

def calculate_spectral_indices(input_folder: str, spectral_indices, stac_source, collection) -> str:
    """
    Calculate spectral indices from raster data, used with profile "urban_analysis" or "crop_condition".
    
    Args:
        input_folder (str): Directory path containing the input raster files for index calculation.
        spectral_indices (list): List of spectral indices to calculate.
            Each element is a string identifier of a spectral index (e.g., "NDVI", "EVI", "EVI2", "SAVI").
    """

    if (stac_source == "bdc" and collection == "AMZ1-WFI-L4-SR-1"):
        pattern_nir = r'_BAND4_'
        pattern_red = r'_BAND3_'
        pattern_blue = r'_BAND1_'
    else:
        pattern_nir = r'_B08_'
        pattern_red = r'_B04_'
        pattern_blue = r'_B02_'
        pattern_swir = r'_B11_'

        files_swir = [
            os.path.join(input_folder, f) for f in os.listdir(input_folder)
            if re.search(pattern_swir, f)
        ]

    files_nir = [
        os.path.join(input_folder, f) for f in os.listdir(input_folder)
        if re.search(pattern_nir, f)
    ]
    
    files_red = [
        os.path.join(input_folder, f) for f in os.listdir(input_folder)
        if re.search(pattern_red, f)
    ]

    files_blue = [
        os.path.join(input_folder, f) for f in os.listdir(input_folder)
        if re.search(pattern_blue, f)
    ]

    for spectral_indice in spectral_indices:

        if spectral_indice == "NDVI":
            for i in range(min(len(files_nir), len(files_red))):
                fix_negatives(files_nir[i])
                fix_negatives(files_red[i])
                if (stac_source == "bdc" and collection == "AMZ1-WFI-L4-SR-1"):  
                    file_name = files_red[i].replace("BAND3","NDVI")
                else:
                    file_name = files_red[i].replace("B04","NDVI")
                ndvi_calc(files_nir[i], files_red[i], file_name)
        
        if spectral_indice == "EVI":
            for i in range(min(len(files_nir), len(files_red))):
                fix_negatives(files_nir[i])
                fix_negatives(files_red[i])
                fix_negatives(files_blue[i])
                if (stac_source == "bdc" and collection == "AMZ1-WFI-L4-SR-1"):  
                    file_name = files_red[i].replace("BAND3","EVI")
                else:
                    file_name = files_red[i].replace("B04","EVI")
                evi_calc(files_nir[i], files_red[i], files_blue[i], file_name)
        
        if spectral_indice == "EVI2":
            for i in range(min(len(files_nir), len(files_red))):
                fix_negatives(files_nir[i])
                fix_negatives(files_red[i])
                if (stac_source == "bdc" and collection == "AMZ1-WFI-L4-SR-1"):  
                    file_name = files_red[i].replace("BAND3","EVI2")
                else:
                    file_name = files_red[i].replace("B04","EVI2")
                evi2_calc(files_nir[i], files_red[i], file_name)
        
        if spectral_indice == "SAVI":
            for i in range(min(len(files_nir), len(files_red))):
                fix_negatives(files_nir[i])
                fix_negatives(files_red[i])
                file_name = files_red[i].replace("B04","SAVI")
                savi_calc(files_nir[i], files_red[i], file_name)
        
        if spectral_indice == "NDBI":
            for i in range(min(len(files_swir), len(files_nir))):
                fix_negatives(files_nir[i])
                fix_negatives(files_swir[i])
                file_name = files_nir[i].replace("B08", "NDBI")
                ndbi_calc(files_swir[i],files_nir[i], file_name)