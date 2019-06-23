#ifndef _MCP3426_H_
#define _MCP3426_H_

int mcp3426_init(const char *path, unsigned addr);
short mcp3426_get(int adc, unsigned channel, unsigned gain);
void mcp3426_close(int adc);

#endif
