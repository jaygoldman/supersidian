//
//  HealthcheckPreferencesView.swift
//  Supersidian
//
//  Healthcheck preferences tab.
//

import SwiftUI

struct HealthcheckPreferencesView: View {
    @ObservedObject var viewModel: PreferencesViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            // Information section
            VStack(alignment: .leading, spacing: 12) {
                Text("What is Healthcheck?")
                    .font(.headline)

                Text("Healthcheck monitoring allows you to track whether your Supersidian syncs are running successfully. When configured, Supersidian will ping your healthcheck URL after each successful sync.")
                    .font(.body)
                    .foregroundStyle(.secondary)

                Text("If syncs fail or stop running, the healthcheck service will alert you via email or other notification methods you configure.")
                    .font(.body)
                    .foregroundStyle(.secondary)

                Link("Set up a free healthcheck at healthchecks.io", destination: URL(string: "https://healthchecks.io")!)
                    .font(.body)
            }
            .padding(.vertical, 8)

            Divider()

            // Enable Healthcheck
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Enable Healthcheck")
                        .fontWeight(.regular)

                    Spacer()

                    Toggle("", isOn: Binding(
                        get: { viewModel.editedConfig.healthcheckEnabled },
                        set: { newValue in
                            var config = viewModel.editedConfig
                            config.healthcheckEnabled = newValue
                            viewModel.updateEdited(config)
                        }
                    ))
                    .toggleStyle(.switch)
                    .labelsHidden()
                }

                Text("Automatically ping a healthcheck URL after each successful sync")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.vertical, 8)

            Divider()

            // Healthcheck URL
            VStack(alignment: .leading, spacing: 8) {
                Text("Healthcheck URL")
                    .fontWeight(.regular)

                TextField("", text: Binding(
                    get: { viewModel.editedConfig.healthcheckUrl ?? "" },
                    set: { newValue in
                        var config = viewModel.editedConfig
                        config.healthcheckUrl = newValue.isEmpty ? nil : newValue
                        viewModel.updateEdited(config)
                    }
                ), prompt: Text("https://hc-ping.com/your-uuid-here"))
                .textFieldStyle(.roundedBorder)
                .disabled(!viewModel.editedConfig.healthcheckEnabled)

                Text("Ping URL for monitoring sync health. Get one from [healthchecks.io](https://healthchecks.io)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.vertical, 8)

            Spacer()
        }
    }
}
