export function canUseCapability(
  enabledCapabilities: readonly string[],
  effectivePermissions: readonly string[],
  capability: string,
  permission: string,
): boolean {
  return enabledCapabilities.includes(capability) && effectivePermissions.includes(permission)
}
