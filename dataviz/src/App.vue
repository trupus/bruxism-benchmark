<template>
  <div id="app">
    <div class="d-flex-column">
      <span>Error: {{ errorMessage }}</span>
      <span>Success: {{ successMessage }}</span>
      <div class="d-flex-row">
        <button @click="sendMessage(JSON.stringify({ action: 'dirs' }))">
          Get dirs
        </button>
        <button @click="makeConnection">Reconnect</button>
        <button @click="sendMessage(JSON.stringify({ action: 'stop' }))">
          Stop streaming
        </button>
      </div>

      <div class="d-flex-row">
        <button
          v-for="dir in dirs"
          :key="dir"
          @click="sendMessage(JSON.stringify({ action: 'stream', dir }))"
        >
          {{ dir }}
        </button>
      </div>
      <div>
        <!-- graphs here -->
        <div class="container" v-if="payload">
          <LineChart
            v-for="(chartData, sensorName) in payload"
            :key="sensorName"
            :labels="chartData.labels"
            :datasets="chartData.datasets"
            :chartId="sensorName"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import LineChart from "@/components/LineChart.vue";

export default {
  name: "App",
  components: { LineChart },
  data: function () {
    return {
      connection: null,
      dirs: [],
      payload: null,
      successMessage: "",
      errorMessage: "",
    };
  },
  methods: {
    sendMessage(message) {
      this.connection.send(message);
    },
    eventHandler(event) {
      const data = JSON.parse(event.data);
      if (data.hasOwnProperty("type")) {
        switch (data.type) {
          case "dirs":
            this.dirs = data.dirs;
            break;
          case "payload":
            this.payload = data.payload;
          default:
            break;
        }
      }

      if (data.hasOwnProperty("success")) {
        this.successMessage = data.success.message;
      }

      if (data.hasOwnProperty("error")) {
        this.errorMessage = data.error.message;
      }
    },
    makeConnection() {
      this.successMessage = "";
      this.errorMessage = "";

      this.connection = new WebSocket("ws://192.168.2.2:1337");

      this.connection.onmessage = this.eventHandler;
      this.connection.onopen = function (event) {
        this.successMessage = "Successfully connected to the websocket server";
      };
      this.connection.onerror = function (event) {
        this.errorMessage = JSON.stringify(event);
      };
    },
  },
  created() {
    this.makeConnection();
  },
};
</script>

<style lang="scss" scoped>
.d-flex-column {
  display: flex;
  flex-direction: column;
}

.d-flex-row {
  display: flex;
}

.container {
  display: grid;
  grid-template-columns: 33% 33% 33%;
  grid-template-rows: auto;
}
</style>