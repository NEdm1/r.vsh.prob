#!/usr/bin/env python

############################################################################
#
# MODULE:    r.viewshed.probable
# AUTHOR(S): Nagy Edmond
# PURPOSE:	 Script for generating raster maps that show how the error
#                present in the DEM might affect the viewshed output.
# COPYRIGHT: (C) 2019 by Nagy Edmond, and the GRASS Development Team
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
############################################################################

#%module
#% description: Creates a probable viewshed raster map from a DEM and input points using r.viewshed and r.random.surface.
#% keyword: raster
#% keyword: r.viewshed
#% keyword: r.random.surface
#% keyword: r.series
#%end

#%option G_OPT_V_INPUT
#% key: vect
#% description: Input observer vector points
#% required: yes
#%end

#%option G_OPT_R_INPUT
#% key: rast
#% description: Input DEM raster
#% required: yes
#%end

#%option G_OPT_R_OUTPUT
#% key: output
#% description: Output raster pattern name (eg. "example_cat2", example = user name)
#% required: yes
#%end

#%option
#% key: rmse
#% type: double
#% description: The root-mean-square error to be introduced
#% required : yes
#%end

#%flag
#% key: c
#% description: Consider the curvature of the earth (current ellipsoid)
#%end

#%flag
#% key: r
#% description: Consider the effect of atmospheric refraction
#%end

#%option
#% key: observer_elevation
#% type: double
#% description: Height of observer
#%answer: 1.75
#% required : no
#%end

#%option
#% key: target_elevation
#% type: double
#% description: Height of targets
#%answer: 1.75
#% required : no
#%end

#%option
#% key: max_distance
#% type: double
#% description: Maximum visibility radius. By default infinity (-1)
#%answer: -1
#% required : no
#%end

#%option
#% key: memory
#% type: integer
#% description: Amount of memory to use (in MB)
#%answer: 500
#% required : no
#%end

#%option
#% key: refraction_coeff
#% type: double
#% description: Refraction coefficient (with flag -r)
#%answer: 0.14286
#% options: 0.0-1.0
#% required : no
#%end

#%option
#% key: num_simulations
#% type: integer
#% description: Number of simulations to test
#%answer: 20
#% required : no
#%end

import sys
import grass.script as grass
from grass.pygrass.modules.shortcuts import raster as r


def main():
    options, flags = grass.parser()
    
    # setup input variables
    rast = options["rast"]
    vect = options["vect"]
    rmse = round(float(options["rmse"]))
    nSim = int(options["num_simulations"])
	
    viewshed_options = {}
    for option in ('observer_elevation', 'target_elevation', 'max_distance', 'memory', 'refraction_coeff'):
        viewshed_options[option] = options[option]

    out = options["output"]

    # setup flagstring
    flagstring = ''
    if flags['r']:
        flagstring += 'r'
    if flags['c']:
        flagstring += 'c'

    # see if the input is valid
    if (int(grass.vector_info_topo(map=vect)['points']) < 1):
        grass.error(_("There are no point features in the input."))

    else:
        # get the input vector points
        points = grass.read_command("v.out.ascii", flags='r', input=vect, type="point", format="point", separator=",").strip()

        # read the input points and parse them
        pointList = []
        for line in points.splitlines():
            if line:
                pointList.append(line.strip().split(','))

        # create the DEM variations
        grass.message(_("Creating DEM variations."))

        for sim in range(nSim):
            # create the random error map
            grass.run_command("r.random.surface", output="tempRandSurf", overwrite=True, distance=((rmse*2)+1)*10, high=(rmse*2)+1)

            # add the error to the inpu DEM
            r.mapcalc("%s = %s + (%s - %i)" % ("tempNewDEM"+str(sim), rast, "tempRandSurf", rmse+1), overwrite=True)

        # run r.viewshed for each point for as many simulations as needed
        grass.message(_("Running the simulations."))

        for point in pointList:
            viewshLst = []

            # run viewsheds for each simulation
            for sim in range(nSim):
                grass.run_command("r.viewshed", overwrite=True, input="tempNewDEM"+str(sim), flags=flagstring+'b',
                                  output="tempViewshPoint"+point[-1]+"Sim"+str(sim), coordinates=point[0]+","+point[1],
                                  **viewshed_options)

                # append simulation to list
                viewshLst.append("tempViewshPoint"+point[-1]+"Sim"+str(sim))

            # create probable viewshed for current point
            grass.run_command("r.series", overwrite=True, quiet=True, input=(",").join(viewshLst), output=out+"_cat"+point[-1], method="average")

        # remove more leftovers
        grass.run_command("g.remove", quiet=True, flags='f', type='raster', pattern="temp*")

    return

if __name__ == "__main__":
    options, flags = grass.parser()
    sys.exit(main())
