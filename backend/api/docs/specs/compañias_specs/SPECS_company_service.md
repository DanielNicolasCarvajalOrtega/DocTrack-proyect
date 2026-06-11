# SPEC — CompanyService
**Módulo:** `app/modules/compañias/service.py`
**Versión:** 1.0
**Estado:** 🟡 En desarrollo

---

## ¿Qué es este documento?

Define el comportamiento esperado de `CompanyService` antes de escribir
o ejecutar cualquier test. Cada sección describe:

- **Qué hace** el método
- **Qué recibe** (inputs)
- **Qué retorna** (outputs)
- **Cuándo falla** (guard clauses → errores esperados)

Los tests en `test_company_service.py` se derivan directamente de este
documento. Si el comportamiento cambia, este archivo se actualiza primero
y los tests después.

---

## Contratos globales

```
- Todos los métodos reciben una Session de SQLAlchemy (db)
- Los repositorios NUNCA se llaman directamente desde fuera del service
- ValueError  → error de negocio (400 en el router)
- PermissionError → sin permisos (403 en el router)
- Los límites (max_*) solo los aplica apply_billing_plan() desde constants.py
- El último admin de una compañía no puede ser degradado ni removido
```

---

## SPEC-001 — `crear_compañia`

### Descripción
Crea una compañía raíz aplicando los límites del plan automáticamente.

### Inputs
| Campo | Tipo | Requerido |
|---|---|---|
| `db` | Session | ✓ |
| `company_data` | dict | ✓ |
| `company_data.name` | str | ✓ |
| `company_data.slug` | str | ✓ |
| `company_data.billing_plan` | BillingPlan | default: prueba |
| `company_data.structure_type` | StructureType | default: simple |

### Output esperado
Objeto `Company` con `max_users_per_plant`, `max_plants`, `max_storage_gb`,
`max_children` aplicados automáticamente desde `BILLING_PLAN_LIMITS`.

### Guard clauses → errores
| ID | Condición | Error | Mensaje esperado |
|---|---|---|---|
| G-001-1 | `structure_type=divisional` con `plan=prueba` | `ValueError` | contiene "no soporta" |
| G-001-2 | `structure_type=corporativo` con `plan=basico` | `ValueError` | contiene "no soporta" |
| G-001-3 | `structure_type=divisional` con `plan=basico` | `ValueError` | contiene "no soporta" |

### Comportamiento esperado
| ID | Escenario | Resultado |
|---|---|---|
| B-001-1 | plan=prueba + structure=simple | Compañía creada con max_plants=1, max_users_per_plant=5 |
| B-001-2 | plan=pro + structure=divisional | Compañía creada con max_plants=20, max_users_per_plant=60 |
| B-001-3 | plan=empresas + structure=corporativo | Compañía creada con max_children=22 |

---

## SPEC-002 — `obtener_compañia`

### Descripción
Retorna los datos completos de una compañía.
Solo admin y auditor pueden ver métricas sensibles.

### Guard clauses → errores
| ID | Condición | Error | Mensaje esperado |
|---|---|---|---|
| G-002-1 | Compañía no existe o inactiva | `ValueError` | contiene "no encontrada" |
| G-002-2 | Usuario con rol supervisor | `PermissionError` | contiene "No tienes permisos" |
| G-002-3 | Usuario con rol técnico | `PermissionError` | contiene "No tienes permisos" |
| G-002-4 | Usuario con rol operador | `PermissionError` | contiene "No tienes permisos" |
| G-002-5 | Usuario no es miembro ni admin del parent | `PermissionError` | contiene "No tienes permisos" |

### Comportamiento esperado
| ID | Escenario | Resultado |
|---|---|---|
| B-002-1 | Usuario con rol admin | Retorna Company |
| B-002-2 | Usuario con rol auditor | Retorna Company |
| B-002-3 | Admin del parent solicita subsidiaria | Retorna Company |

---

## SPEC-003 — `actualizar_compañia`

### Descripción
Actualiza campos editables. Los campos `max_*` no son editables.

### Guard clauses → errores
| ID | Condición | Error | Mensaje esperado |
|---|---|---|---|
| G-003-1 | Usuario no es admin | `PermissionError` | contiene "No tienes permisos" |
| G-003-2 | `structure_type=corporativo` con `plan=pro` | `ValueError` | contiene "no soporta" |
| G-003-3 | Compañía no existe | `ValueError` | contiene "no encontrada" |

### Comportamiento esperado
| ID | Escenario | Resultado |
|---|---|---|
| B-003-1 | Admin actualiza `name` | Retorna Company actualizada |
| B-003-2 | Admin del parent actualiza subsidiaria | Retorna Company actualizada |
| B-003-3 | Admin cambia `structure_type` compatible | Retorna Company actualizada |

---

## SPEC-004 — `cambiar_plan`

### Descripción
Sube el plan y aplica los nuevos límites automáticamente.

### Guard clauses → errores
| ID | Condición | Error | Mensaje esperado |
|---|---|---|---|
| G-004-1 | No es admin | `PermissionError` | contiene "No tienes permisos" |
| G-004-2 | Nuevo plan no soporta subsidiarias y tiene hijos activos | `ValueError` | contiene "subsidiarias activas" |
| G-004-3 | `structure_type` actual incompatible con nuevo plan | `ValueError` | contiene "no soporta" |
| G-004-4 | Hijos activos superan `max_children` del nuevo plan | `ValueError` | contiene "máximo" |

### Comportamiento esperado
| ID | Escenario | Resultado |
|---|---|---|
| B-004-1 | Sube de prueba a basico sin hijos | Plan actualizado, límites aplicados |
| B-004-2 | Sube de basico a pro | Plan actualizado, `max_plants=20` |

---

## SPEC-005 — `eliminar_compañia`

### Descripción
Soft delete. No se puede eliminar si tiene dependientes activos.

### Guard clauses → errores
| ID | Condición | Error | Mensaje esperado |
|---|---|---|---|
| G-005-1 | No es admin | `PermissionError` | contiene "No tienes permisos" |
| G-005-2 | Tiene subsidiarias activas | `ValueError` | contiene "subsidiarias activas" |
| G-005-3 | Tiene más de 1 usuario activo | `ValueError` | contiene "usuarios activos" |

### Comportamiento esperado
| ID | Escenario | Resultado |
|---|---|---|
| B-005-1 | Admin elimina compañía sin dependientes | `True` |

---

## SPEC-006 — `crear_subsidiaria`

### Descripción
Crea una subsidiaria bajo el parent. Solo el admin del parent puede crearla.

### Guard clauses → errores
| ID | Condición | Error | Mensaje esperado |
|---|---|---|---|
| G-006-1 | No es admin del parent | `PermissionError` | contiene "Solo un administrador" |
| G-006-2 | Plan del parent es `prueba` | `ValueError` | contiene "no permite crear subsidiarias" |
| G-006-3 | Hijos activos >= `max_children` del parent | `ValueError` | contiene "límite" |

### Comportamiento esperado
| ID | Escenario | Resultado |
|---|---|---|
| B-006-1 | Admin crea subsidiaria con plan basico (max_children=1, hijos=0) | Retorna Company hija |
| B-006-2 | Admin crea subsidiaria con plan pro (max_children=6, hijos=3) | Retorna Company hija |

---

## SPEC-007 — `agregar_usuario`

### Descripción
Agrega un usuario a la compañía. Solo admin puede hacerlo.

### Guard clauses → errores
| ID | Condición | Error | Mensaje esperado |
|---|---|---|---|
| G-007-1 | No es admin ni admin del parent | `PermissionError` | contiene "No tienes permisos" |
| G-007-2 | Usuario ya es miembro activo | `ValueError` | contiene "ya es miembro" |

### Comportamiento esperado
| ID | Escenario | Resultado |
|---|---|---|
| B-007-1 | Admin agrega usuario con rol técnico | Retorna CompanyUser |
| B-007-2 | Admin del parent agrega usuario a subsidiaria | Retorna CompanyUser |

---

## SPEC-008 — `remover_usuario`

### Descripción
Soft delete de membresía.

### Guard clauses → errores
| ID | Condición | Error | Mensaje esperado |
|---|---|---|---|
| G-008-1 | No es admin | `PermissionError` | contiene "No tienes permisos" |
| G-008-2 | Target no es miembro activo | `ValueError` | contiene "no es miembro" |
| G-008-3 | Target es el único admin | `ValueError` | contiene "único administrador" |

### Comportamiento esperado
| ID | Escenario | Resultado |
|---|---|---|
| B-008-1 | Admin remueve técnico | `True` |
| B-008-2 | Admin remueve admin (existen 2 admins) | `True` |

---

## SPEC-009 — `cambiar_rol_usuario`

### Descripción
Cambia el rol de un miembro.

### Guard clauses → errores
| ID | Condición | Error | Mensaje esperado |
|---|---|---|---|
| G-009-1 | No es admin | `PermissionError` | contiene "Solo un administrador" |
| G-009-2 | Intenta cambiar su propio rol | `ValueError` | contiene "propio rol" |
| G-009-3 | Degrada al único admin | `ValueError` | contiene "único administrador" |
| G-009-4 | Target no es miembro activo | `ValueError` | contiene "no es miembro" |

### Comportamiento esperado
| ID | Escenario | Resultado |
|---|---|---|
| B-009-1 | Admin cambia técnico → supervisor | Retorna CompanyUser con nuevo rol |
| B-009-2 | Admin degrada admin → técnico (existen 2 admins) | Retorna CompanyUser con nuevo rol |

---

## SPEC-010 — `degradar_plan`

### Descripción
Baja el plan. Verifica internamente los bloqueos antes de persistir.

### Guard clauses → errores
| ID | Condición | Error | Mensaje esperado |
|---|---|---|---|
| G-010-1 | Tiene subsidiarias que superan el límite del nuevo plan | `ValueError` | contiene "Resuelve los siguientes bloqueos" |
| G-010-2 | `structure_type` incompatible con nuevo plan | `ValueError` | contiene "Resuelve los siguientes bloqueos" |

### Comportamiento esperado
| ID | Escenario | Resultado |
|---|---|---|
| B-010-1 | Sin bloqueos → degrada pro a basico | Retorna Company con nuevos límites |

---

## SPEC-011 — `verificar_bloqueos_downgrade`

### Comportamiento esperado
| ID | Escenario | Resultado |
|---|---|---|
| B-011-1 | Compañía limpia | `{ puede_degradar: True, bloqueos: [] }` |
| B-011-2 | Tiene 4 hijos, nuevo plan permite 1 | `{ puede_degradar: False, bloqueos: [contiene "subsidiarias"] }` |
| B-011-3 | `structure_type=corporativo`, nuevo plan=pro | `{ puede_degradar: False, bloqueos: [contiene "estructura"] }` |

---

## SPEC-012 — `eliminar_subsidiarias_en_cascada`

### Comportamiento esperado
| ID | Escenario | Resultado |
|---|---|---|
| B-012-1 | 3 subsidiarias limpias | `{ eliminadas: 3, fallidas: [], puede_degradar_ya: True }` |
| B-012-2 | 1 subsidiaria tiene usuarios activos | aparece en `fallidas` con motivo |
| B-012-3 | 1 subsidiaria tiene sub-subsidiarias | aparece en `fallidas` con motivo |
| B-012-4 | Sin subsidiarias | `{ eliminadas: 0, mensaje: "No hay subsidiarias activas." }` |

---

## Cobertura esperada

| Métodos | Tests | Guards | Comportamientos |
|---|---|---|---|
| 12 | 47 | 27 | 20 |

**Meta de cobertura:** 90% de `service.py`