{{- define "bundleutils.name" -}}
bundleutils
{{- end }}

{{- define "bundleutils.chart" -}}
{{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{- define "bundleutils.fullname" -}}
{{ printf "bundleutils" (include "bundleutils.name" .) }}-{{ .Release.Name }}
{{- end }}
