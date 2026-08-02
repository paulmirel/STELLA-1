# palette function
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel
import displayio

def make_palette():
    # TBD make a color name dictionary
    palette = displayio.Palette(40)
    palette[0] = 0x000000 # black
    palette[1] = 0xA0522D # brown
    palette[2] = 0xFF0000 # red
    palette[3] = 0xFF8C00 # orange
    palette[4] = 0xFFFF00 # yellow
    palette[5] = 0x00FF00 # green
    palette[6] = 0x0000FF # blue
    palette[7] = 0x9400D3 # violet
    palette[8] = 0x808080 # grey
    palette[9] = 0xFFFFFF # white
    palette[10] = 0xFF99FF # light
    palette[11] = 0xFF751A # heat
    palette[12] = 0x66CCFF # light blue, air analyzer
    palette[13] = 0x6FDC6F # plants
    palette[14] = 0xB366FF # time place #0xCE954B
    palette[15] = 0x8C8C8C # dark grey
    palette[16] = 0x00998F # burst
    palette[17] = 0x0066FF # border
    palette[18] = 0x009900 # GPS flag
    palette[19] = 0xCCCCCC # light grey
    palette[20] = 0x00CC00 # remote sens green
    palette[21] = 0x00CCBE # sensors
    palette[22] = 0xA6A6A6 # medium grey, return
    palette[23] = 0xFF6666 # medium red, not used yet
    palette[24] = 0xBF8040 # soil #0x996633
    palette[25] = 0x7E00DB # blueviolet, 410nm
    palette[26] = 0x2300FF # blue, 435nm
    palette[27] = 0x007BFF # royalblue, 460nm
    palette[28] = 0x00EAFF # darkturquoise,485nm
    palette[29] = 0x00FF00 # lime, 510nm
    palette[30] = 0x70FF00 # chartreuse, 535nm
    palette[31] = 0xC3FF00 # greenyellow, 560nm
    palette[32] = 0xFFEF00 # yellow, 585nm
    palette[33] = 0xFF9B00 # orange, 610nm
    palette[34] = 0xFE0000 # red1, 645nm
    palette[35] = 0xDF0000 # red2, 680nm
    palette[36] = 0xC90000 # red3, 705nm
    palette[37] = 0xB10000 # firebrick, 730nm
    palette[38] = 0x940000 # darkred, 760nm
    return palette
