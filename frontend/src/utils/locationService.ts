export interface LocationData {
  latitude: number;
  longitude: number;
  address?: string;
  city?: string;
  country?: string;
}

export interface LocationError {
  code: number;
  message: string;
}

class LocationService {
  private static instance: LocationService;
  private currentLocation: LocationData | null = null;

  private constructor() {}

  public static getInstance(): LocationService {
    if (!LocationService.instance) {
      LocationService.instance = new LocationService();
    }
    return LocationService.instance;
  }

  public async getCurrentLocation(): Promise<LocationData> {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject({
          code: 0,
          message: 'Geolocation is not supported by this browser.'
        });
        return;
      }

      const options = {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 300000 // 5 minutes
      };

      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const locationData: LocationData = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude
          };

          try {
            // Try to get address from coordinates
            const address = await this.reverseGeocode(locationData.latitude, locationData.longitude);
            locationData.address = address.address;
            locationData.city = address.city;
            locationData.country = address.country;
          } catch (error) {
            console.warn('Reverse geocoding failed:', error);
          }

          this.currentLocation = locationData;
          resolve(locationData);
        },
        (error) => {
          let errorMessage = 'Unknown location error';
          
          switch (error.code) {
            case error.PERMISSION_DENIED:
              errorMessage = 'Location access denied by user.';
              break;
            case error.POSITION_UNAVAILABLE:
              errorMessage = 'Location information is unavailable.';
              break;
            case error.TIMEOUT:
              errorMessage = 'Location request timed out.';
              break;
          }

          reject({
            code: error.code,
            message: errorMessage
          });
        },
        options
      );
    });
  }

  public async reverseGeocode(latitude: number, longitude: number): Promise<{
    address: string;
    city: string;
    country: string;
  }> {
    try {
      // Using a free geocoding service (you can replace with Google Maps API if you have a key)
      const response = await fetch(
        `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${latitude}&longitude=${longitude}&localityLanguage=en`
      );
      
      if (!response.ok) {
        throw new Error('Geocoding service unavailable');
      }

      const data = await response.json();
      
      return {
        address: data.locality || data.city || 'Unknown location',
        city: data.city || data.locality || 'Unknown city',
        country: data.countryName || 'Unknown country'
      };
    } catch (error) {
      console.error('Reverse geocoding error:', error);
      throw error;
    }
  }

  public async geocodeAddress(address: string): Promise<LocationData> {
    try {
      // Using a free geocoding service
      const response = await fetch(
        `https://api.opencagedata.com/geocode/v1/json?q=${encodeURIComponent(address)}&key=YOUR_API_KEY&limit=1`
      );
      
      if (!response.ok) {
        throw new Error('Geocoding service unavailable');
      }

      const data = await response.json();
      
      if (data.results && data.results.length > 0) {
        const result = data.results[0];
        return {
          latitude: result.geometry.lat,
          longitude: result.geometry.lng,
          address: result.formatted,
          city: result.components.city || result.components.town || result.components.village,
          country: result.components.country
        };
      } else {
        throw new Error('Address not found');
      }
    } catch (error) {
      console.error('Geocoding error:', error);
      throw error;
    }
  }

  public calculateDistance(
    lat1: number,
    lon1: number,
    lat2: number,
    lon2: number
  ): number {
    const R = 6371; // Radius of the Earth in kilometers
    const dLat = this.deg2rad(lat2 - lat1);
    const dLon = this.deg2rad(lon2 - lon1);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(this.deg2rad(lat1)) *
        Math.cos(this.deg2rad(lat2)) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const distance = R * c; // Distance in kilometers
    return Math.round(distance * 100) / 100; // Round to 2 decimal places
  }

  private deg2rad(deg: number): number {
    return deg * (Math.PI / 180);
  }

  public getCachedLocation(): LocationData | null {
    return this.currentLocation;
  }

  public clearCache(): void {
    this.currentLocation = null;
  }
}

export default LocationService;