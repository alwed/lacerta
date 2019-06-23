#ifndef _PITS_INFO_H_
#define _PITS_INFO_H_

#include <stdint.h>

struct pits_info {
	uint64_t time;		/* ms since POSIX epoch			*/

	uint32_t lat;		/* latitude · 1e7 / °			*/
	uint32_t lon;		/* longitude · 1e7 / °			*/
	uint32_t alt;		/* altitude / mm			*/
	uint32_t alt_max;  	/* maximum altitude / mm		*/
	uint32_t speed_g;  	/* ground_speed / cm/s			*/
	int32_t speed_v;  	/* ascent_rate / cm/s			*/
	int32_t heading;  	/* heading · 1e5 / °			*/
	uint16_t gps_status;	/* space_vehicle(6), fix(2), model(8)	*/

	uint16_t Ts;		/* temperature system / K; U10.6	*/
	uint16_t Ti;    	/* temperature intern / K; U10.6	*/
	uint16_t Te;    	/* temperature extern / K; U10.6	*/
	int32_t p;      	/* atmospheric pressure / Pa		*/

	uint16_t vbat;  	/* battery voltage / V; U6.10		*/
	uint16_t isys;  	/* system current (5V rail) / A; U2.14	*/
};

#endif
