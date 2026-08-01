{{- define "educode.name" -}}educode{{- end -}}
{{- define "educode.fullname" -}}{{ printf "%s-%s" .Release.Name (include "educode.name" .) | trunc 63 | trimSuffix "-" }}{{- end -}}
{{- define "educode.labels" -}}
app.kubernetes.io/name: {{ include "educode.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
