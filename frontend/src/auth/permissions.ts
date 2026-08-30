export const ADMINISTRATION_PERMISSIONS = [
  'user.view', 'role.view', 'permission.view', 'audit.view', 'module.view',
] as const

export const MASTER_VIEW_PERMISSIONS = [
  'location.view', 'manufacturer.view', 'instrument_type.view', 'material.view',
] as const

export const LABORATORY_MASTER_VIEW_PERMISSIONS = [
  'test.view', 'method.view', 'specification.view',
] as const
