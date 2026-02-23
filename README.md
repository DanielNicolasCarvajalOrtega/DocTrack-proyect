# DocTrack - Sistema de Gestión Documental y Trazabilidad Industrial

## 🎯 Descripción General
**DocTrack** es una plataforma SaaS B2B Multi-Tenant diseñada específicamente para el sector industrial. Su función principal es centralizar la gestión de la documentación técnica de maquinaria, llevar una trazabilidad inmutable de las operaciones y administrar los flujos de mantenimiento (preventivo, correctivo y predictivo) de forma segura y aislada para múltiples empresas.

## 💡 Propósito
El propósito central del sistema se resume en su propuesta de valor: *"Cada máquina, cada documento, cada persona — conectados en tiempo real"*. 
DocTrack busca garantizar el cumplimiento normativo (compliance) facilitando las auditorías, y empoderar a los operarios en planta dándoles acceso inmediato a la información crítica y actualizada que necesitan para operar y reparar equipos de forma segura.

## ⚠️ El Problema Encontrado
Actualmente, las empresas industriales (como Carozzi, Nestlé o Unilever) sufren de una gestión de la información ineficiente y riesgosa:
* **Dispersión de información:** Los manuales y certificados están perdidos en carpetas físicas, Google Drive o SharePoint hasta en whatsapp.
* **Tiempos prolongados de inactividad (Downtime):** Las máquinas pasan horas detenidas porque los técnicos tardan demasiado en rastrear el historial de fallas y el manual de reparación correcto.
* **Falta de trazabilidad:** No hay forma de comprobar si un operario realmente leyó las instrucciones de seguridad antes de usar una máquina.
* **Procesos manuales:** El mantenimiento se sigue gestionando mediante hojas de cálculo (Excel) o papel.
* **Riesgo normativo:** Los documentos importantes (como certificados de calibración) vencen sin que nadie lo note porque no existen alertas automáticas.
* **Falta de control de acceso estructurado:** Ausencia de permisos granulares, lo que permite que empleados accedan a información confidencial de plantas o áreas que no les corresponden.
* **Desconexión en planta:** El operario frente a la máquina no tiene acceso rápido a los manuales para resolver problemas en el momento.

## ✅ Cómo se va a solucionar (La Solución)
DocTrack resuelve esta brecha mediante la digitalización y automatización del piso de planta:
1. **Acceso Instantáneo (Códigos QR):** Cada máquina física tendrá un código QR único. El operario lo escanea con su móvil y accede al instante a todos los manuales, certificados y tareas de esa máquina específica.
2. **Trazabilidad Automática:** El sistema exige y registra automáticamente las "Confirmaciones de lectura" (quién, qué documento y en qué fecha exacta), generando un historial auditable.
3. **Mantenimiento Digitalizado:** Todo el flujo de trabajo (creación de la tarea por el supervisor → ejecución del técnico → cierre de la tarea) se gestiona desde la plataforma.
4. **Alertas Inteligentes:** El sistema avisa proactivamente (ej. 30 días antes) cuando un documento o certificado está a punto de vencer.
5. **Aislamiento Multi-Tenant:** Una arquitectura backend robusta asegura que los datos de cada cliente estén 100% separados y seguros, permitiendo escalar el modelo de negocio SaaS.
