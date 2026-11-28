package com.example.erp.app

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.unit.dp
import com.example.erp.core.Point
import com.example.erp.core.Trace

/**
 * Data trace (test builds): the last actions, and for each one the eight points its data passes, green or red,
 * with the reason at the point that failed. Phone: list, then detail. Tablet (wide): list and detail side by side.
 */
@Composable
fun TraceScreen(traces: List<Trace>, showValues: Boolean, onAddSample: (() -> Unit)?, onTryConnection: (() -> Unit)? = null) {
    var openId by rememberSaveable { mutableStateOf<String?>(null) }
    val open = traces.firstOrNull { it.id == openId }
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val wide = maxWidth >= 840.dp
        if (wide) {
            Row(Modifier.fillMaxSize().padding(Look.Gap), horizontalArrangement = Arrangement.spacedBy(Look.Gap)) {
                TraceList(traces, open?.id, onAddSample, onTryConnection, Modifier.weight(1f)) { openId = it }
                Column(Modifier.weight(1.4f)) {
                    if (open != null) TraceDetail(open, showValues, onBack = null)
                    else Text("Choose an action on the left.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
                }
            }
        } else if (open != null) {
            Column(Modifier.fillMaxSize().padding(Look.Gap)) { TraceDetail(open, showValues, onBack = { openId = null }) }
        } else {
            TraceList(traces, null, onAddSample, onTryConnection, Modifier.fillMaxSize().padding(Look.Gap)) { openId = it }
        }
    }
}

@Composable
private fun TraceList(
    traces: List<Trace>,
    selected: String?,
    onAddSample: (() -> Unit)?,
    onTryConnection: (() -> Unit)?,
    modifier: Modifier,
    onOpen: (String) -> Unit,
) {
    Column(modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Data trace", style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
        if (traces.isEmpty()) {
            Text("No actions yet. Each save you make in the app appears here with the points its data passed.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
        }
        for (trace in traces) {
            val fault = trace.fault
            RowCard(
                R.drawable.ic_trace,
                trace.action,
                when {
                    fault != null -> "Stopped at ${fault.point.ordinal + 1}. ${fault.point.label}"
                    trace.complete -> "Read back the same"
                    else -> ""
                },
                pill = when {
                    fault != null -> StatusKind.BAD to "Failed"
                    trace.complete -> StatusKind.OK to "Saved"
                    else -> StatusKind.NONE to "In progress"
                },
                selected = trace.id == selected,
                onClick = { onOpen(trace.id) },
            )
        }
        if (onAddSample != null) MainButton("Add a sample trace (test builds)", onAddSample)
        if (onTryConnection != null) OutlineButton("Try the connection (test builds)", onTryConnection)
    }
}

@Composable
private fun TraceDetail(trace: Trace, showValues: Boolean, onBack: (() -> Unit)?) {
    val clipboard = LocalClipboardManager.current
    Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(trace.action, style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
        Panel {
            for (point in Point.entries) {
                val mark = trace.marks.lastOrNull { it.point == point }
                val kind = when {
                    mark == null -> StatusKind.NONE
                    mark.ok -> StatusKind.OK
                    else -> StatusKind.BAD
                }
                val took = mark?.tookMs?.let { " · $it ms" }.orEmpty()
                Status(kind, "${point.ordinal + 1}. ${point.label}: ${kind.word}$took")
                if (mark != null && mark.note.isNotEmpty()) Text(mark.note, style = MaterialTheme.typography.bodyMedium)
                if (mark != null && !mark.ok) Text("Usually means: ${point.faultMeans}.", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
                if (showValues && mark?.detail != null) Text(mark.detail!!, style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
            }
        }
        MainButton("Copy this trace", { clipboard.setText(AnnotatedString(trace.report(withValues = showValues))) })
        if (onBack != null) MainButton("Back to the list", onBack)
    }
}
