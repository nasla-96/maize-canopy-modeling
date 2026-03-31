#include <iostream>
#include <string>
#include <vector>
#include <boost/property_tree/ptree.hpp>
#include <boost/property_tree/ini_parser.hpp>
#include "Context.h"
#include "SolarPosition.h"
#include "Visualizer.h"
#include "RadiationModel.h"
#include <chrono>
#include <filesystem>

using namespace helios;
using namespace boost::property_tree;
namespace fs = std::filesystem; // Alias for filesystem namespa

// Function to read config file and return both paths
void readConfigFile(const std::string& filename, std::string& fieldPath) {
    ptree pt;
    read_ini(filename, pt);

    // Read OBJ file paths from config file
    // plantPath = pt.get<std::string>("Paths.objfilepath");
    fieldPath = pt.get<std::string>("Paths.fieldfilepath");
}

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <config_file_path>" << std::endl;
        return 1;
    }

    // Start the timer
    // auto start = std::chrono::steady_clock::now();

    //---- inputs ----//
    int UTC = 5;            // hours from UTC

    // setting location as Ames, IA
    // float latitude = 42.03;   //latitude in degrees
    // float longitude = 93.63; //longitude in degrees

    // setting location as Peace river, Alberta, Canada
    float latitude = 57.13;   //latitude in degrees
    float longitude = 117.28; //longitude in degrees

    // setting location as Thomas County, Kansas
    // float latitude = 39.3703;   //latitude in degrees
    // float longitude = 101.0712; //longitude in degrees

    Date date(7, 8, 2020);
    float pressure = 101300; // atmospheric pressure (Pa)
    float temperature = 300; // air temperature (K)
    float humidity = 0.5;    // relative humidity (-)
    float turbidity = 0.05;

    // Output file stream for writing to CSV
    std::ofstream csvFile("/work/mech-ai-scratch/nasla/PAR_model/GA_rotate10_120x24_56canada/PAR_values.csv", std::ios::app);
    std::ofstream csvFile1("/work/mech-ai-scratch/nasla/PAR_model/GA_rotate10_120x24_56canada/PAR_values_total.csv", std::ios::app);
    // if (csvFile.tellp() == 0) { // Check if the file is empty
    //     csvFile << "chromosome_name, hour, PAR_plant, PAR_ground1\n"; // Write header
    // }

    // Read OBJ file path from config file
    std::string configFilePath = argv[1];
    std::string fieldPath;
    readConfigFile(configFilePath, fieldPath);

    // Extract filename for the plant file path
    std::string chromosome_name = fs::path(fieldPath).filename().string();

    // Initialize Context
    Context context;

    // Add geometry from OBJ files
    std::vector<uint> UUID1, UUID2, UUID_ground1;
    // const char* plantFilename = plantPath.c_str();
    const char* fieldFilename = fieldPath.c_str();
    // UUID1 = context.loadOBJ(plantFilename, make_vec3(0.0, 0.0, 1.05), 0, SphericalCoord(0, 0, 0), RGB::green);
    UUID1 = context.loadOBJ(fieldFilename, make_vec3(0.0, 0.0, 1.05), 0, SphericalCoord(0, 0, 0), RGB::green);
    UUID_ground1 = context.addTile(make_vec3(0, 0, 0), make_vec2(5.0, 3.0), make_SphericalCoord(0, 0), make_int2(500, 500));

    float rho1,tau1,eps1; // rho1 = 0.38f;
    rho1 = 0.05f;
    context.setPrimitiveData(UUID1, "reflectivity_PAR", rho1);
    tau1 = 0.05f; //transmissivity value
    context.setPrimitiveData( UUID1, "transmissivity_PAR",  tau1);
    // eps1 = 0.90f; //emissivity value
    // context.setPrimitiveData( UUID1, "emissivity_PAR",  eps1);
    // add two-sided flag
    context.setPrimitiveData( UUID1, "twosided_flag", uint(1) );

    // Initialize the solar position model
    SolarPosition solarposition(UTC, latitude, longitude, &context); // initialize the solar position model

    // Initialize the radiation model
    RadiationModel radiationmodel(&context); // initialize the radiation model
    uint SunSource = radiationmodel.addCollimatedRadiationSource(); // add the source (sun), we'll set its direction later

    radiationmodel.addRadiationBand("PAR");
    radiationmodel.setDirectRayCount("PAR", 1000); // set the ray count for source
    radiationmodel.disableEmission("PAR");
    radiationmodel.setScatteringDepth("PAR", 5); // set the number of scattering iterations
    radiationmodel.updateGeometry();

    // Variable to accumulate the total PAR value
    float cumulative_PAR = 0.0;
    
    // Loop over various hours of the day (7:00 thru 21:00)
    context.setDate(date); // set the date, which will not change
    for (int hour = 9; hour < 19; hour++) {
        // Set the current time and calculate the associated sun direction
        context.setTime(0, hour); // set the current time for this iteration
        vec3 sdir = solarposition.getSunDirectionVector(); // get the solar direction from plug-in
        radiationmodel.setSourcePosition(SunSource, sdir); // set the radiation source direction in radiation model

        // Calculate incoming solar fluxes for the current time
        float Rflux = solarposition.getSolarFlux(pressure, temperature, humidity, turbidity);
        float fdiff = solarposition.getDiffuseFraction(pressure, temperature, humidity, turbidity); // fraction of Rflux that is diffuse
        radiationmodel.setSourceFlux(SunSource, "PAR", Rflux * (1 - fdiff)); // set the direct flux: Rflux*(1-fdiff)
        radiationmodel.enforcePeriodicBoundary("xy");

        // Run the model
        radiationmodel.runBand("PAR");

        float PAR_plant;
        context.calculatePrimitiveDataAreaWeightedSum(UUID1, "radiation_flux_PAR", PAR_plant); 
        float PAR_ground1;
        context.calculatePrimitiveDataAreaWeightedSum(UUID_ground1, "radiation_flux_PAR", PAR_ground1);

        // Accumulate the PAR value
        cumulative_PAR += PAR_plant;

        // Print the PAR value in a specific format
        csvFile << chromosome_name << ", " << hour << ", " << PAR_plant << ", " << PAR_ground1 << "\n";
        csvFile.flush();
    }
    // Print the cumulative PAR value after the loop
    std::cout << "PAR_VALUE: " << cumulative_PAR << std::endl;

    // Print the PAR value in a specific format
    csvFile1 << chromosome_name << ", " << cumulative_PAR << "\n";
    csvFile1.flush();

    // End the timer
    // auto end = std::chrono::steady_clock::now();
    // auto duration = std::chrono::duration_cast<std::chrono::seconds>(end - start).count();
    // std::cout << "Time taken for simulation: " << duration << " seconds" << std::endl;

    return 0;
}
